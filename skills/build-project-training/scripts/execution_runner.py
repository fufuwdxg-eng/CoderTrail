"""Collect replayable local test evidence. This runner is NOT a security sandbox."""
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MAX_LOG = 1024 * 1024
MAX_JSON = 8 * MAX_LOG


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    data = Path(path).read_bytes()
    if len(data) > MAX_JSON:
        raise ValueError('JSON exceeds size limit')
    return json.loads(data)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def inside(root, name):
    """Only explicit relative files, no traversal or symlink components."""
    rel = PurePosixPath(name)
    if not name or rel.is_absolute() or '..' in rel.parts or '\\' in name or ':' in name:
        raise ValueError(f'unsafe relative path: {name}')
    path = Path(root)
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError(f'symlink is not accepted: {name}')
    if not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('path escapes root')
    return path


def string_list(value):
    return isinstance(value, list) and bool(value) and all(isinstance(v, str) and v.strip() for v in value)


def validate_manifest(m):
    if m.get('schema_version') != 1 or not isinstance(m.get('project_id'), str) or not m['project_id'].strip():
        raise ValueError('manifest version and project_id required')
    languages = m.get('languages')
    if not string_list(languages) or len(set(languages)) != len(languages):
        raise ValueError('unique languages required')
    mode = m.get('implementation_mode')
    if mode not in ('single', 'variants', 'collaboration') or (mode == 'single') != (len(languages) == 1):
        raise ValueError('implementation mode and language count disagree')
    files = m.get('files')
    if not string_list(files) or len(set(files)) != len(files):
        raise ValueError('explicit files required, without duplicates')
    for f in files:
        inside(Path.cwd(), f)
    steps = m.get('steps')
    if not isinstance(steps, list) or not steps:
        raise ValueError('execution steps required')
    ids = set()
    for s in steps:
        if not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'].replace('-', '').replace('_', '').isalnum() or s['id'] in ids:
            raise ValueError('unique simple step IDs required')
        ids.add(s['id'])
        if s.get('role') not in ('version', 'build', 'test', 'integration') or not string_list(s.get('argv')):
            raise ValueError('invalid step role or argv')
        if not string_list(s.get('languages')) or not set(s['languages']).issubset(languages):
            raise ValueError('step languages must belong to manifest')
        timeout = s.get('timeout_seconds', 10)
        if type(timeout) not in (int, float) or not 0 < timeout <= 60:
            raise ValueError('step timeout must be 0..60 seconds')
        if s['role'] in ('test', 'integration'):
            if s.get('format') == 'cases':
                cases = s.get('cases')
                if not isinstance(cases, list) or not cases or len(cases) > 200:
                    raise ValueError('1..200 independent cases required')
                case_ids = set()
                for case in cases:
                    if not isinstance(case.get('id'), str) or not case['id'] or case['id'] in case_ids:
                        raise ValueError('unique case IDs required')
                    case_ids.add(case['id'])
                    if (not isinstance(case.get('stdin', ''), str) or not isinstance(case.get('stdout'), str)
                            or type(case.get('exit_code', 0)) is not int):
                        raise ValueError('case needs explicit expected stdout and integer exit code')
                    if case.get('category') not in ('normal', 'boundary', 'error', 'property', 'recovery', 'integration'):
                        raise ValueError('case category required')
            elif s.get('format') == 'junit':
                inside(Path.cwd(), s.get('result_file', ''))
                if s.get('category') not in ('normal', 'boundary', 'error', 'property', 'recovery', 'integration'):
                    raise ValueError('JUnit suite category required')
            else:
                raise ValueError('tests must use cases or fresh JUnit XML; exit code alone is insufficient')
    version_langs = set().union(*(set(s['languages']) for s in steps if s['role'] == 'version'))
    test_langs = set().union(*(set(s['languages']) for s in steps if s['role'] == 'test'))
    if version_langs != set(languages) or test_langs != set(languages):
        raise ValueError('every language needs version capture and behavioral tests')
    if mode == 'collaboration' and not any(s['role'] == 'integration' and set(s['languages']) == set(languages) for s in steps):
        raise ValueError('collaboration needs an integration suite covering all languages')


def stop_process(proc):
    if os.name == 'posix':
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif proc.poll() is None:
        proc.kill()


def execute(argv, cwd, logs, name, stdin='', timeout=10):
    argv = [sys.executable if arg == '{python}' else arg for arg in argv]
    outpath, errpath = logs/(name+'.stdout.txt'), logs/(name+'.stderr.txt')
    env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'SystemRoot', 'TEMP', 'TMP') if key in os.environ}
    env.update(PYTHONDONTWRITEBYTECODE='1')
    started = time.monotonic()
    error, code = None, None
    with outpath.open('wb') as out, errpath.open('wb') as err, tempfile.TemporaryFile() as inp:
        inp.write(stdin.encode()); inp.seek(0)
        try:
            proc = subprocess.Popen(argv, cwd=cwd, stdin=inp, stdout=out, stderr=err,
                                    env=env, shell=False, start_new_session=os.name == 'posix')
            try:
                while proc.poll() is None:
                    if time.monotonic()-started > timeout:
                        error = 'timeout'; break
                    if outpath.stat().st_size > MAX_LOG or errpath.stat().st_size > MAX_LOG:
                        error = 'output_limit'; break
                    time.sleep(.02)
            finally:
                stop_process(proc)
                code = proc.wait()
        except OSError as exc:
            error = f'launch_error: {exc}'
    for path in (outpath, errpath):
        if path.stat().st_size > MAX_LOG:
            error = 'output_limit'
            with path.open('r+b') as f:
                f.truncate(MAX_LOG)
    return {'argv': argv, 'exit_code': code, 'error': error,
            'elapsed_seconds': round(time.monotonic()-started, 6),
            'stdout': 'logs/'+outpath.name, 'stderr': 'logs/'+errpath.name,
            'stdout_sha256': digest(outpath.read_bytes()), 'stderr_sha256': digest(errpath.read_bytes())}


def parse_junit(data):
    if len(data) > MAX_JSON or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('unsafe or oversized XML')
    root = ET.fromstring(data)
    cases = []
    for node in root.iter():
        if node.tag.split('}')[-1] == 'testcase':
            tags = {child.tag.split('}')[-1] for child in node}
            status = 'failed' if tags & {'error', 'failure'} else ('skipped' if 'skipped' in tags else 'passed')
            cases.append({'id': node.get('classname', '')+'::'+node.get('name', ''), 'status': status})
    return cases


def derive_tests(step, invocations, root, junit_path=None):
    """Recompute outcomes from captured output, never trust declared counts."""
    if step['format'] == 'cases':
        if len(invocations) != len(step['cases']):
            raise ValueError('case invocation count differs')
        result = []
        for case, run in zip(step['cases'], invocations):
            stdout = inside(root, run['stdout']).read_bytes()
            stderr = inside(root, run['stderr']).read_bytes()
            passed = (run['error'] is None and run['exit_code'] == case.get('exit_code', 0)
                      and stdout == case['stdout'].encode('utf-8')
                      and ('stderr' not in case or stderr == case['stderr'].encode('utf-8')))
            result.append({'id': case['id'], 'status': 'passed' if passed else 'failed', 'category': case['category']})
        return result
    if len(invocations) != 1 or not junit_path:
        return []
    cases = parse_junit(inside(root, junit_path).read_bytes())
    for case in cases:
        case['category'] = step['category']
    return cases


def summarize(manifest, steps, source_unchanged):
    tests = [case for step in steps for case in step.get('tests', [])]
    counts = {s: sum(t['status'] == s for t in tests) for s in ('passed', 'failed', 'skipped')}
    executed = counts['passed']+counts['failed']
    incomplete = len(steps) != len(manifest['steps']) or any(s.get('incomplete') for s in steps)
    failed = not source_unchanged or counts['failed'] > 0 or any(s.get('failed') for s in steps)
    by_language = {}
    for lang in manifest['languages']:
        relevant = [t for s in steps if s['role'] == 'test' and lang in s['languages'] for t in s.get('tests', [])]
        by_language[lang] = {'passed': sum(t['status'] == 'passed' for t in relevant),
                             'failed': sum(t['status'] == 'failed' for t in relevant),
                             'skipped': sum(t['status'] == 'skipped' for t in relevant)}
        if not relevant or not any(t['status'] in ('passed', 'failed') for t in relevant):
            incomplete = True
    if not executed or counts['skipped']:
        incomplete = True
    integrations = [s for s in steps if s['role'] == 'integration']
    integration_passed = bool(integrations) and all(s.get('tests') and not s.get('failed') and not s.get('incomplete') for s in integrations)
    if manifest['implementation_mode'] == 'collaboration' and not integration_passed:
        incomplete = True
    return {'status': 'failed' if failed else ('incomplete' if incomplete else 'passed'),
            'executed': executed, **counts, 'by_language': by_language,
            'integration_passed': integration_passed,
            'categories': sorted({t['category'] for t in tests})}


def step_flags(definition, item):
    runs = item['invocations']
    incomplete = not runs or any(r['error'] for r in runs)
    failed = False
    if definition['role'] in ('version', 'build') or definition.get('format') == 'junit':
        failed = any(r['exit_code'] not in (0, None) for r in runs)
    if definition['role'] in ('test', 'integration'):
        failed = failed or any(t['status'] == 'failed' for t in item.get('tests', []))
        incomplete = incomplete or not item.get('tests') or any(t['status'] == 'skipped' for t in item.get('tests', []))
    return {'failed': bool(failed), 'incomplete': bool(incomplete)}


def run_project(manifest, project, out):
    validate_manifest(manifest)
    project, out = Path(project).resolve(), Path(out).resolve()
    if out.is_relative_to(project):
        raise ValueError('evidence output must be outside project directory')
    out.mkdir(parents=True, exist_ok=False)
    snapshot, logs = out/'snapshot', out/'logs'
    snapshot.mkdir(); logs.mkdir()
    hashes = {}
    for name in manifest['files']:
        source = inside(project, name)
        if not source.is_file():
            raise ValueError(f'missing project file: {name}')
        target = inside(snapshot, name); target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        hashes[name] = digest(target.read_bytes())
    write_json(out/'manifest.json', manifest)
    steps = []
    with tempfile.TemporaryDirectory(prefix='training-run-') as temp:
        work = Path(temp)/'project'; shutil.copytree(snapshot, work)
        for step in manifest['steps']:
            invocations = []
            item = {'id': step['id'], 'role': step['role'], 'languages': step['languages'], 'invocations': invocations}
            if step['role'] in ('version', 'build'):
                invocations.append(execute(step['argv'], work, logs, step['id'], timeout=step.get('timeout_seconds', 10)))
            elif step['format'] == 'cases':
                for i, case in enumerate(step['cases']):
                    invocations.append(execute(step['argv'], work, logs, f'{step["id"]}-{i}', case.get('stdin', ''), step.get('timeout_seconds', 10)))
                item['tests'] = derive_tests(step, invocations, out)
            else:
                result = inside(work, step['result_file'])
                if result.exists():
                    result.unlink()
                result.parent.mkdir(parents=True, exist_ok=True)
                invocations.append(execute(step['argv'], work, logs, step['id'], timeout=step.get('timeout_seconds', 10)))
                if result.is_file() and not result.is_symlink():
                    data = result.read_bytes()
                    item['junit_path'] = f'logs/{step["id"]}.xml'
                    item['junit_sha256'] = digest(data)
                    inside(out, item['junit_path']).write_bytes(data)
                    try:
                        item['tests'] = derive_tests(step, invocations, out, item['junit_path'])
                    except (ValueError, ET.ParseError) as exc:
                        item['parse_error'] = str(exc)
                if not item.get('tests'):
                    item['incomplete'] = True
            item.update(step_flags(step, item))
            steps.append(item)
            if step['role'] in ('version', 'build') and (item.get('failed') or item.get('incomplete')):
                break
        unchanged = all(inside(work, n).is_file() and digest(inside(work, n).read_bytes()) == h for n, h in hashes.items())
    report = {'schema_version': 1, 'collector': 'project-training-runner-1',
              'created_at': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'collector_python': sys.version, 'project_id': manifest['project_id'],
              'languages': manifest['languages'], 'implementation_mode': manifest['implementation_mode'],
              'files': hashes, 'code_sha256': digest(canonical(hashes)),
              'manifest_sha256': digest(canonical(manifest)), 'source_unchanged': unchanged,
              'steps': steps, 'summary': summarize(manifest, steps, unchanged)}
    write_json(out/'execution.json', report)
    return report


def verify_execution(path, expected_sha256=None):
    path = Path(path).resolve(); root = path.parent
    raw = path.read_bytes()
    if expected_sha256 and digest(raw) != expected_sha256:
        raise ValueError('execution report hash differs')
    report = load_json(path); manifest = load_json(root/'manifest.json')
    validate_manifest(manifest)
    if report.get('collector') != 'project-training-runner-1' or report.get('schema_version') != 1:
        raise ValueError('unsupported collector')
    if digest(canonical(manifest)) != report['manifest_sha256']:
        raise ValueError('test manifest changed')
    hashes = {n: digest(inside(root/'snapshot', n).read_bytes()) for n in manifest['files']}
    if hashes != report['files'] or digest(canonical(hashes)) != report['code_sha256']:
        raise ValueError('source snapshot changed')
    if any(report[k] != manifest[k] for k in ('languages', 'implementation_mode', 'project_id')):
        raise ValueError('report scope differs from manifest')
    for definition, step in zip(manifest['steps'], report['steps']):
        if any(step[k] != definition[k] for k in ('id', 'role', 'languages')):
            raise ValueError('step identity differs')
        expected_argv = [sys.executable if arg == '{python}' else arg for arg in definition['argv']]
        for run in step['invocations']:
            # An archived {python} run can come from a different interpreter path.
            comparable = list(run['argv'])
            if definition['argv'][0] == '{python}':
                comparable[0] = sys.executable
            if comparable != expected_argv:
                raise ValueError('executed command differs from manifest')
            for stream in ('stdout', 'stderr'):
                if digest(inside(root, run[stream]).read_bytes()) != run[stream+'_sha256']:
                    raise ValueError('execution log changed')
        if definition['role'] in ('test', 'integration'):
            if step.get('junit_path') and digest(inside(root, step['junit_path']).read_bytes()) != step['junit_sha256']:
                raise ValueError('JUnit evidence changed')
            try:
                recomputed = derive_tests(definition, step['invocations'], root, step.get('junit_path'))
            except (ValueError, ET.ParseError):
                recomputed = []
            if recomputed != step.get('tests', []):
                raise ValueError('test outcomes differ from captured evidence')
        flags = step_flags(definition, step)
        if any(step.get(key) != value for key, value in flags.items()):
            raise ValueError('step status differs from captured execution')
    if summarize(manifest, report['steps'], report['source_unchanged']) != report['summary']:
        raise ValueError('summary differs from evidence')
    return report


def execution_ref(path, archive_ref):
    return {'local_path': str(Path(path).resolve()), 'sha256': digest(Path(path).read_bytes()), 'archive_ref': archive_ref}


def resolve_execution(ref):
    cache = os.environ.get('TRAINING_EVIDENCE_ROOT')
    if cache:
        path = Path(cache)/ref['sha256']/'execution.json'
        if path.is_file():
            return path
    return Path(ref.get('local_path', ''))
