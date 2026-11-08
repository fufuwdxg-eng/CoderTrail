#!/usr/bin/env python3
"""Validate declared evidence, scores and diversity; never infer source quality."""
import argparse
import copy
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from urllib.parse import urlparse
from execution_runner import verify_execution, resolve_execution

WEIGHTS = dict(correctness=20, readability=10, maintainability=10,
               testability=10, performance=10, architecture=15,
               documentation=5, engineering=10, reliability=10)
AXES = dict(domain_tags=.20, concept_tags=.45,
            artifact_tags=.10, engineering_tags=.25)
DEFAULT_BANK = Path(__file__).resolve().parents[1]/'assets/question-bank.json'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_languages(value):
    """Open vocabulary of canonical IDs; language is metadata, never a novelty axis."""
    return (isinstance(value, list) and bool(value)
            and all(isinstance(v, str) and re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', v)
                    for v in value) and len(set(value)) == len(value))


def language_context_issues(context):
    if not isinstance(context, dict):
        return ['language_context required']
    targets = context.get('targets')
    if not valid_languages(targets):
        return ['language_context.targets must contain unique canonical language IDs']
    issues = []
    mode = context.get('mode')
    if mode not in ('single', 'mixed') or (mode == 'single' and len(targets) != 1) or (mode == 'mixed' and len(targets) < 2):
        issues.append('language mode and target count disagree')
    if not nonempty(context.get('selection_basis')):
        issues.append('language selection basis required')
    profiles = context.get('toolchains', [])
    if (not isinstance(profiles, list) or not all(isinstance(p, dict) for p in profiles)
            or len(profiles) != len(targets)
            or {p.get('language') for p in profiles} != set(targets)):
        issues.append('one toolchain profile per target language required')
    elif any(not all(nonempty(p.get(k)) for k in ('version', 'toolchain', 'platform'))
             or p['version'].strip().lower() in ('latest', 'current', 'unknown') for p in profiles):
        issues.append('language version, toolchain and platform must be pinned')
    return issues


def assess(record):
    require(isinstance(record, dict), 'review must be an object')
    require(record.get('kind') in ('external_source', 'reference_implementation'),
            'invalid review kind')
    require(nonempty(record.get('id')), 'review id required')
    scores = record.get('scores', {})
    require(set(scores) == set(WEIGHTS), 'exactly nine score dimensions required')
    missing, failures = [], []
    evidence = record.get('evidence', [])
    require(isinstance(evidence, list), 'evidence must be a list')
    by_id = {}
    for item in evidence:
        require(isinstance(item, dict) and nonempty(item.get('id')), 'evidence id required')
        require(item['id'] not in by_id, 'duplicate evidence id')
        by_id[item['id']] = item
    def has_evidence(ids, kind=None):
        return (isinstance(ids, list) and bool(ids)
                and all(i in by_id and nonempty(by_id[i].get('locator'))
                        and nonempty(by_id[i].get('observation')) for i in ids)
                and (kind is None or any(by_id[i].get('kind') == kind for i in ids)))
    total, complete = Decimal(0), True
    for key, weight in WEIGHTS.items():
        item = scores[key]
        require(isinstance(item, dict), f'{key}: score object required')
        rating = item.get('rating')
        if rating is None:
            complete = False; missing.append(f'{key}: unscored')
        else:
            require(type(rating) is int and 0 <= rating <= 10,
                    f'{key}: rating must be an integer 0..10 or null')
            total += Decimal(weight)*rating/10
            if rating <= 2:
                failures.append(f'{key}: severe deficiency cannot be offset by total score')
        if not nonempty(item.get('rationale')) or not has_evidence(item.get('evidence_ids')):
            missing.append(f'{key}: rationale or evidence missing')
        if not nonempty(item.get('limitations')):
            missing.append(f'{key}: limitations assessment missing')
    if complete and total < 85:
        failures.append('total below 85')
    if complete and 85 <= total <= 88:
        calibration = record.get('calibration', {})
        if (calibration.get('decision') != 'confirm' or not nonempty(calibration.get('reviewer'))
                or calibration.get('method') not in ('independent-review', 'blind-rerating')
                or not nonempty(calibration.get('rationale')) or not has_evidence(calibration.get('evidence_ids'))):
            missing.append('borderline 85..88 requires documented independent or blind recalibration')
    for key, floor in [('correctness',9), ('testability',8), ('reliability',8)]:
        rating = scores[key].get('rating')
        if rating is not None and rating < floor:
            failures.append(f'{key} below {floor}')
    source = record.get('source', {})
    languages = source.get('languages')
    if not valid_languages(languages):
        missing.append('source.languages missing or invalid; do not infer from filename')
        languages = []
    for key in ('url','revision','scope','evidence_archive_ref'):
        if not nonempty(source.get(key)):
            missing.append(f'source.{key} missing')
    if source.get('revision','').lower() in ('head','main','master','latest'):
        missing.append('source revision is mutable')
    if not re.fullmatch(r'[a-fA-F0-9]{64}', source.get('code_sha256','')):
        missing.append('source code SHA256 missing')
    if record['kind'] == 'external_source':
        for key in ('url','project_url'):
            if urlparse(source.get(key,'')).scheme not in ('http','https'):
                missing.append(f'external {key} must be a web source')
    license_info = source.get('license', {})
    if license_info.get('reuse_allowed') is False:
        failures.append('reuse not permitted')
    elif license_info.get('reuse_allowed') is not True:
        missing.append('reuse permission unknown')
    if not all(nonempty(license_info.get(k)) for k in ('id','locator','obligations')):
        missing.append('license evidence or obligations missing')
    try:
        date.fromisoformat(record.get('reviewed_at',''))
    except (TypeError,ValueError):
        missing.append('reviewed_at must be ISO date')
    v = record.get('verification', {})
    for key in ('code_inspected','tests_executed','independent_checks'):
        if v.get(key) is not True:
            missing.append(f'{key} not completed')
    if v.get('tests_passed') is False:
        failures.append('tests failed')
    elif v.get('tests_passed') is not True:
        missing.append('test result unknown')
    findings = v.get('critical_findings')
    if not isinstance(findings, list):
        missing.append('critical findings assessment missing')
    elif findings:
        failures.append('unresolved critical findings')
    if not isinstance(v.get('commands'), list) or not v['commands'] or not all(map(nonempty,v['commands'])):
        missing.append('executed test commands missing')
    if not nonempty(v.get('environment')) or not has_evidence(v.get('evidence_ids'), 'test'):
        missing.append('test environment or execution evidence missing')
    checks = v.get('language_checks', [])
    if (not isinstance(checks, list) or not all(isinstance(c, dict) for c in checks)
            or len(checks) != len(languages)
            or {c.get('language') for c in checks} != set(languages)):
        missing.append('one execution check per source language required')
    else:
        for check in checks:
            lang = check['language']
            commands = check.get('commands')
            if (not nonempty(check.get('environment')) or not isinstance(commands, list)
                    or not commands or not all(map(nonempty, commands))
                    or not has_evidence(check.get('evidence_ids'), 'test')):
                missing.append(f'{lang}: runtime environment, commands or test evidence missing')
            if check.get('tests_passed') is False:
                failures.append(f'{lang}: tests failed')
            elif check.get('tests_passed') is not True:
                missing.append(f'{lang}: test result unknown')
    if not any(e.get('kind') == 'source' and nonempty(e.get('locator'))
               and nonempty(e.get('observation')) for e in evidence):
        missing.append('source inspection evidence missing')
    refs = v.get('execution_refs', [])
    executions = []
    if not isinstance(refs, list) or not refs:
        missing.append('captured execution bundle required; declarations alone are insufficient')
    else:
        for ref in refs:
            if (not isinstance(ref, dict) or not re.fullmatch(r'[a-f0-9]{64}', str(ref.get('sha256', '')))
                    or not nonempty(ref.get('archive_ref'))):
                missing.append('execution reference needs report SHA256 and persistent archive'); continue
            try:
                run = verify_execution(resolve_execution(ref), ref['sha256'])
            except (OSError, ValueError, KeyError, TypeError) as exc:
                missing.append('execution evidence unavailable or invalid: '+str(exc)); continue
            if run['code_sha256'] != source.get('code_sha256'):
                failures.append('executed source snapshot differs from reviewed code'); continue
            executions.append(run)
            if run['summary']['status'] == 'failed': failures.append('captured execution failed')
            elif run['summary']['status'] != 'passed': missing.append('captured execution incomplete')
    verified_languages = set().union(*(set(r['languages']) for r in executions))
    if verified_languages != set(languages):
        missing.append('execution evidence must cover exactly the reviewed languages')
    mode = source.get('implementation_mode', 'single' if len(languages) == 1 else None)
    if mode not in ('single', 'variants', 'collaboration'):
        missing.append('multi-language implementation mode required')
    if any(r['implementation_mode'] != mode for r in executions):
        failures.append('execution mode differs from reviewed scope')
    if mode == 'collaboration' and not any(r['summary']['integration_passed'] for r in executions):
        missing.append('multi-language collaboration requires captured integration tests')
    if record.get('revoked') is True:
        failures.append('review revoked: '+str(record.get('revocation_reason','')))
    status = 'rejected' if failures else ('pending' if missing else 'eligible')
    return {'status':status, 'total':float(total) if complete else None,
            'failures':failures, 'missing':missing, 'weights':WEIGHTS}


def history_signature(bank):
    data = json.dumps(bank['exercises'],sort_keys=True,ensure_ascii=False,separators=(',',':'))
    return hashlib.sha256(data.encode()).hexdigest()


def tagset(item, axis):
    return set(item.get(axis, []))


def similarity(a,b):
    value = 0.0
    for axis,weight in AXES.items():
        x,y = tagset(a,axis),tagset(b,axis)
        value += weight*len(x&y)/len(x|y) if x|y else 0
    return value


def duplicate_core(a,b):
    return (tagset(a,'concept_tags') == tagset(b,'concept_tags')
            and tagset(a,'engineering_tags') == tagset(b,'engineering_tags'))


def resolve_mix(count=15, request=None):
    """Resolve an explicit difficulty request; round ties toward one more basic task."""
    require(type(count) is int and count > 0, 'count must be a positive integer')
    request = {'mode':'default', 'value':None, 'basis':''} if request is None else request
    require(isinstance(request, dict), 'difficulty_request must be an object')
    mode, value = request.get('mode'), request.get('value')
    if mode != 'default':
        require(nonempty(request.get('basis')), 'custom difficulty mix needs the user request basis')

    def number(value):
        require(type(value) in (int, float, str), 'ratio/percentage must be a finite number')
        try:
            result = Fraction(str(value))
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError('ratio/percentage must be a finite number') from exc
        require(result >= 0, 'ratio/percentage must be nonnegative')
        return result

    if mode == 'default':
        require(value is None, 'default mix cannot contain a custom value')
        require(count >= 3, 'small batches need explicit difficulty counts')
        exact = Fraction(3)
    elif mode == 'counts':
        require(isinstance(value, list) and len(value) == 2
                and all(type(v) is int and v >= 0 for v in value)
                and sum(value) == count, 'basic and advanced counts must sum to count')
        exact = Fraction(value[0])
    elif mode == 'ratio':
        require(isinstance(value, list) and len(value) == 2, 'ratio needs [basic, advanced]')
        basic, advanced = map(number, value)
        require(basic + advanced > 0, 'ratio cannot be 0:0')
        exact = count * basic / (basic + advanced)
    elif mode == 'percentage':
        percent = number(value)
        require(percent <= 100, 'basic percentage must be within 0..100')
        exact = count * percent / 100
    else:
        raise ValueError('difficulty mode must be default, counts, ratio or percentage')
    basic = (2 * exact.numerator + exact.denominator) // (2 * exact.denominator)
    return {'count':count, 'basic_count':basic, 'advanced_count':count-basic,
            'rounding_applied':exact != basic}


def check_plan(plan, bank, final=False):
    issues, nearest = [], []
    context = plan.get('language_context')
    issues.extend(language_context_issues(context))
    targets = context.get('targets', []) if isinstance(context, dict) else []
    targets = set(targets) if valid_languages(targets) else set()
    implemented = set()
    questions = plan.get('questions', [])
    n, basic = plan.get('count',15), plan.get('basic_count',3)
    require(type(n) is int and n > 0 and type(basic) is int and 0 <= basic <= n,
            'invalid count/basic_count')
    advanced = plan.get('advanced_count', n-basic)
    require(type(advanced) is int and advanced >= 0, 'advanced_count must be a nonnegative integer')
    require(isinstance(questions,list), 'questions must be a list')
    if n != 15 and not nonempty(plan.get('scope_override_reason')):
        issues.append('nondefault batch size needs an explicit user-request basis')
    mix = {'count':n, 'basic_count':basic, 'advanced_count':advanced, 'rounding_applied':False}
    request = plan.get('difficulty_request')
    if request is not None:
        try:
            resolved = resolve_mix(n, request)
            if (basic, advanced) != (resolved['basic_count'], resolved['advanced_count']):
                issues.append('difficulty counts differ from the user request')
            mix['rounding_applied'] = resolved['rounding_applied']
        except ValueError as exc:
            issues.append(str(exc))
    elif basic != 3 and not nonempty(plan.get('scope_override_reason')):
        issues.append('custom difficulty mix needs difficulty_request or a legacy request basis')
    if basic + advanced != n: issues.append('basic and advanced counts must sum to count')
    if len(questions) != n: issues.append('question count mismatch')
    if sum(q.get('level')=='basic' for q in questions) != basic:
        issues.append('basic count mismatch')
    if sum(q.get('level')=='advanced' for q in questions) != advanced:
        issues.append('advanced count mismatch')
    if any(q.get('level') not in ('basic','advanced') for q in questions):
        issues.append('levels must be basic or advanced')
    ids = [q.get('id') for q in questions]
    if not all(map(nonempty, ids)) or len(set(ids)) != len(ids):
        issues.append('missing or duplicate question ids')
    if set(ids) & {q['id'] for q in bank['exercises']}:
        issues.append('question id already exists in history')
    if plan.get('history_signature') != history_signature(bank):
        issues.append('history changed or not read; refresh plan')
    research = plan.get('research', {})
    if research.get('history_checked') is not True or not nonempty(research.get('completed_at')):
        issues.append('pre-authoring research incomplete')
    queries=research.get('query_log',[])
    if not queries or not all(isinstance(q,dict) and nonempty(q.get('query'))
                              and nonempty(q.get('date')) for q in queries):
        issues.append('web research query log missing')
    candidates=research.get('candidates',[])
    candidate_map={}
    signatures=set()
    research_domains=set()
    for c in candidates:
        if not isinstance(c,dict) or not all(nonempty(c.get(k)) for k in ('id','url','project_url','scope','disposition')):
            issues.append('incomplete candidate record');continue
        if any(urlparse(c[k]).scheme not in ('http','https') for k in ('url','project_url')):
            issues.append('candidate must link to an actual web source')
        domains=c.get('domain_tags',[])
        if not valid_languages(c.get('languages')):
            issues.append('candidate language classification missing or invalid')
        if not isinstance(domains,list) or not domains or not all(map(nonempty,domains)):
            issues.append('candidate domain classification missing')
        else:research_domains.update(domains)
        sig=(c['project_url'].rstrip('/').lower(),c['scope'].strip().lower())
        if c['id'] in candidate_map or sig in signatures:
            issues.append('duplicate research candidate')
        candidate_map[c['id']]=c;signatures.add(sig)
    if len(signatures) < 3*n: issues.append(f'fewer than {3*n} distinct researched candidates')
    required_domains=1 if nonempty(plan.get('single_domain_reason')) else min(n,8)
    if len(research_domains)<required_domains:issues.append('research domain coverage too narrow')
    covers={axis:set() for axis in AXES}
    past={axis:set().union(*(tagset(q,axis) for q in bank['exercises'])) for axis in AXES}
    new_questions,projects = 0,{}
    reviews = bank['reviews']
    for q in questions:
        languages = q.get('implementation_languages')
        if not valid_languages(languages):
            issues.append(f'{q.get("id")}: implementation languages required')
            languages = []
        qlanguages = set(languages)
        implemented.update(qlanguages)
        if not qlanguages.issubset(targets):
            issues.append(f'{q.get("id")}: implementation language outside selected targets')
        adaptations = q.get('cross_language_adaptations', [])
        if not isinstance(adaptations, list) or not all(isinstance(a, dict) for a in adaptations):
            issues.append(f'{q.get("id")}: invalid cross-language adaptations')
            adaptations = []
        if not nonempty(q.get('title')) or not nonempty(q.get('novelty_note')):
            issues.append(f'{q.get("id")}: title/novelty explanation missing')
        difficulty = q.get('difficulty', {})
        dimensions = ('modeling', 'algorithm', 'design', 'debugging')
        if (not isinstance(difficulty, dict) or not all(type(difficulty.get(k)) is int and 1 <= difficulty[k] <= 4 for k in dimensions)
                or not nonempty(difficulty.get('rationale')) or not nonempty(difficulty.get('calibration_basis'))
                or not isinstance(difficulty.get('prerequisites'), list) or not all(map(nonempty,difficulty['prerequisites']))
                or not isinstance(difficulty.get('learning_goals'), list) or not difficulty['learning_goals']
                or not all(map(nonempty,difficulty['learning_goals'])) or type(difficulty.get('estimated_minutes')) is not int
                or difficulty['estimated_minutes'] <= 0):
            issues.append(f'{q.get("id")}: difficulty profile incomplete')
        elif q.get('level') == 'basic' and max(difficulty[k] for k in dimensions) > 2:
            issues.append(f'{q.get("id")}: basic difficulty exceeds calibrated range')
        elif q.get('level') == 'advanced' and max(difficulty[k] for k in dimensions) < 3:
            issues.append(f'{q.get("id")}: advanced difficulty lacks a substantive challenge')
        if q.get('task_type') not in ('build', 'debug', 'refactor', 'extend', 'performance', 'review'):
            issues.append(f'{q.get("id")}: task type required')
        for axis in AXES:
            tags=q.get(axis,[])
            if not isinstance(tags,list) or not tags or not all(isinstance(t,str) and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',t) for t in tags):
                issues.append(f'{q.get("id")}: invalid {axis}')
            else: covers[axis].update(tags)
        if any(tagset(q,axis)-past[axis] for axis in AXES):new_questions+=1
        comparison=q.get('candidate_ids',[])
        if (not isinstance(comparison,list) or len(set(comparison))<2
            or any(i not in candidate_map for i in comparison)
            or len({candidate_map[i]['project_url'].rstrip('/').lower() for i in comparison if i in candidate_map})<2):
            issues.append(f'{q.get("id")}: compare two independent candidates')
        used=q.get('source_review_ids',[])
        if not isinstance(used,list) or not used:
            issues.append(f'{q.get("id")}: no qualified external source')
            used=[]
        source_targets = q.get('source_language_targets')
        if source_targets is None and len(qlanguages) == 1:
            source_targets = {rid: languages for rid in used}
        if (not isinstance(source_targets, dict) or set(source_targets) != set(used)
                or any(not valid_languages(langs) or not set(langs).issubset(qlanguages)
                       for langs in source_targets.values())):
            issues.append(f'{q.get("id")}: map each source to the implementation languages it supports')
            source_targets = {}
        elif set().union(*(set(langs) for langs in source_targets.values())) != qlanguages:
            issues.append(f'{q.get("id")}: source language assignments do not cover the question')
        qprojects=set()
        for rid in used:
            r=reviews.get(rid)
            if rid not in comparison:issues.append(f'{rid}: used source absent from comparison')
            if not r or r.get('kind')!='external_source' or assess(r)['status']!='eligible':
                issues.append(f'{rid}: source is not eligible');continue
            project=r['source']['project_url'].rstrip('/').lower()
            if rid in candidate_map and candidate_map[rid]['project_url'].rstrip('/').lower()!=project:
                issues.append(f'{rid}: candidate and reviewed project disagree')
            source_languages = set(r['source']['languages'])
            candidate_languages = candidate_map.get(rid, {}).get('languages')
            if rid in candidate_map and (not valid_languages(candidate_languages)
                    or set(candidate_languages) != source_languages):
                issues.append(f'{rid}: candidate and reviewed languages disagree')
            unmatched = set(source_targets.get(rid, [])) - source_languages
            if unmatched and not any(a.get('source_review_id') == rid
                    and valid_languages(a.get('target_languages'))
                    and set(a['target_languages']) == unmatched
                    and nonempty(a.get('semantic_risks')) and nonempty(a.get('verification_plan'))
                    for a in adaptations):
                issues.append(f'{q.get("id")}: cross-language adaptation from {rid} needs semantic and verification analysis')
            qprojects.add(project)
        for repo in qprojects:projects[repo]=projects.get(repo,0)+1
        if final:
            ref=reviews.get(q.get('reference_review_id'))
            if (not ref or ref.get('kind')!='reference_implementation'
                or not reference_eligible(ref, bank)
                or not set(used).issubset(set(ref.get('parent_review_ids',[])))):
                issues.append(f'{q.get("id")}: final implementation not separately approved')
            elif set(ref['source']['languages']) != qlanguages:
                issues.append(f'{q.get("id")}: final implementation languages do not match question')
        if bank['exercises']:
            old=max(bank['exercises'],key=lambda old:similarity(q,old))
            nearest.append({'id':q.get('id'),'nearest_id':old['id'],
                            'similarity':round(similarity(q,old),4)})
        for old in bank['exercises']+questions[:questions.index(q)]:
            if duplicate_core(q,old) or similarity(q,old)>=.75-1e-12:
                issues.append(f'{q.get("id")}: repeats {old.get("id")}')
    minimums=dict(domain_tags=min(n,8),concept_tags=min(n,8),
                  artifact_tags=min(n,5),engineering_tags=min(n,5))
    if implemented != targets:
        issues.append('question implementations must cover exactly the selected languages')
    if nonempty(plan.get('single_domain_reason')):minimums['domain_tags']=1
    for axis,minimum in minimums.items():
        if len(covers[axis])<minimum:issues.append(f'{axis}: fewer than {minimum} coverage tags')
    additions={axis:sorted(covers[axis]-past[axis]) for axis in AXES}
    substantive = []
    for q in questions:
        claim = q.get('novelty_evidence', {})
        if claim and claim.get('kind') in ('combination', 'constraint', 'depth'):
            prior = [old for old in bank['exercises'] if old['id'] in claim.get('compared_ids', [])]
            axes = claim.get('axes', [])
            targets_for_claim = {axis: sorted(tagset(q, axis)) for axis in axes if axis in AXES}
            already_combined = bool(prior) and any(all(tagset(q, a) == tagset(old, a) for a in axes) for old in bank['exercises'])
            reviewed = claim.get('review', {})
            valid = (len(set(axes)) >= 2 and all(a in AXES for a in axes) and bool(prior)
                     and nonempty(claim.get('delta')) and nonempty(claim.get('acceptance'))
                     and reviewed.get('approved') is True and nonempty(reviewed.get('reviewer'))
                     and nonempty(reviewed.get('evidence_ref')) and not already_combined)
            if not valid:
                issues.append(f'{q.get("id")}: unsupported substantive novelty claim')
            else:
                fingerprint = hashlib.sha256(json.dumps(targets_for_claim,sort_keys=True).encode()).hexdigest()
                substantive.append((q['id'], fingerprint, set(axes)))
    original_addition_count = sum(map(len, additions.values()))
    substantive_axes = set().union(*(s[2] for s in substantive))
    all_new_axes = {a for a, tags in additions.items() if tags} | substantive_axes
    expansion_ids = {q['id'] for q in questions if any(tagset(q,a)-past[a] for a in AXES)} | {s[0] for s in substantive}
    if original_addition_count+len({s[1] for s in substantive}) < min(3,n) or len(all_new_axes)<min(2,n):
        issues.append('insufficient cumulative breadth increase')
    new_questions = len(expansion_ids)
    if new_questions<math.ceil(.4*n):issues.append('fewer than 40% of questions expand coverage')
    if len(projects)<math.ceil(n/2):issues.append('too few independent upstream projects')
    if any(count>math.ceil(n/5) for count in projects.values()):
        issues.append('too many questions from one upstream project')
    return {'status':'pass' if not issues else 'blocked','issues':sorted(set(issues)),
            'difficulty_mix':mix,
            'coverage':{a:len(v) for a,v in covers.items()},'new_coverage':additions,
            'substantive_expansions':[{'id':s[0],'fingerprint':s[1],'axes':sorted(s[2])} for s in substantive],
            'expanding_questions':new_questions,'nearest_history':nearest}


@contextmanager
def edit_bank(path):
    path=Path(path)
    # The skill executes on Linux/WSL. Serialize readers that will mutate.
    import fcntl
    lock=path.with_suffix(path.suffix+'.lock')
    with lock.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        bank=read_json(path)
        yield bank
        fd,name=tempfile.mkstemp(prefix='.bank-',suffix='.json',dir=path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as out:
                json.dump(bank,out,ensure_ascii=False,indent=2);out.write('\n')
                out.flush();os.fsync(out.fileno())
            os.replace(name,path)
        finally:
            if os.path.exists(name):os.unlink(name)
        # Keep the lock inode stable for other processes; exclude it from Git.


def add_review(bank,record):
    report=assess(record)
    require(report['status']=='eligible',json.dumps(report,ensure_ascii=False))
    if record['kind']=='reference_implementation':
        parents=record.get('parent_review_ids',[])
        require(parents,'reference implementation needs qualified parents')
        for rid in parents:
            parent=bank['reviews'].get(rid)
            require(parent and parent.get('kind')=='external_source'
                    and assess(parent)['status']=='eligible','parent source is not eligible')
        require(reference_eligible(record, bank), 'reference variants or overall evidence are incomplete')
    old=bank['reviews'].get(record['id'])
    require(old is None or old==record,'review id conflict; use a new versioned id')
    bank['reviews'][record['id']]=copy.deepcopy(record)
    return report


def reference_eligible(record, bank):
    if assess(record)['status'] != 'eligible':
        return False
    if record.get('kind') != 'reference_implementation':
        return False
    parents = record.get('parent_review_ids', [])
    if not isinstance(parents, list) or not parents:
        return False
    for rid in parents:
        parent = bank.get('reviews', {}).get(rid)
        if not parent or parent.get('kind') != 'external_source' or assess(parent)['status'] != 'eligible':
            return False
    if record.get('source', {}).get('implementation_mode') != 'variants':
        return True
    variants = record.get('variant_review_ids', {})
    languages = record['source']['languages']
    if not isinstance(variants, dict) or set(variants) != set(languages):
        return False
    parent_files={}
    for ref in record['verification']['execution_refs']:
        parent_files.update(verify_execution(resolve_execution(ref),ref['sha256'])['files'])
    for lang, rid in variants.items():
        item = bank['reviews'].get(rid)
        if (not item or item.get('kind') != 'reference_implementation' or item['source'].get('languages') != [lang]
                or not reference_eligible(item, bank)
                or not set(item.get('parent_review_ids', [])).issubset(record.get('parent_review_ids', []))):
            return False
        for ref in item['verification']['execution_refs']:
            files=verify_execution(resolve_execution(ref),ref['sha256'])['files']
            if not all(parent_files.get(name)==sha for name,sha in files.items()):
                return False
    return True


def record_batch(bank,plan):
    require(nonempty(plan.get('batch_id')),'batch_id required')
    existing=[b for b in bank['batches'] if b['id']==plan['batch_id']]
    require(not existing,'batch already recorded; do not append twice')
    report=check_plan(plan,bank,final=True)
    require(report['status']=='pass',json.dumps(report,ensure_ascii=False))
    artifact=plan.get('artifact',{})
    persistent=(nonempty(artifact.get('library_file_id')) or
                urlparse(artifact.get('url','')).scheme in ('http','https'))
    require(persistent,'saved artifact reference required')
    require(nonempty(plan.get('research',{}).get('archive_ref')),'persistent research archive required')
    v=plan.get('validation',{})
    require(all(v.get(k) is True for k in ('all_code_executed','extracted_code_verified',
                'all_pages_reviewed','artifact_saved')),'delivery validation incomplete')
    for q in plan['questions']:
        item=copy.deepcopy(q)
        item.update(status='delivered',batch_id=plan['batch_id'],artifact=artifact)
        bank['exercises'].append(item)
    bank['batches'].append({'id':plan['batch_id'],'artifact':artifact,
                            'difficulty_mix':report['difficulty_mix'],
                            'difficulty_request':copy.deepcopy(plan.get('difficulty_request')),
                            'scope_override_reason':plan.get('scope_override_reason'),
                            'language_context':copy.deepcopy(plan['language_context']),
                            'research':plan['research'],'validation':v,
                            'diversity_report':report})
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank',type=Path,default=DEFAULT_BANK)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ('score','add-review','check-plan','record-batch'):
        sub=commands.add_parser(name);sub.add_argument('input',type=Path)
        if name=='check-plan':sub.add_argument('--final',action='store_true')
    commands.add_parser('stats')
    mix=commands.add_parser('mix',help='Resolve basic/advanced counts without editing the bank')
    mix.add_argument('--count',type=int,default=15);mix.add_argument('--basis',default='')
    choice=mix.add_mutually_exclusive_group()
    choice.add_argument('--counts',type=int,nargs=2,metavar=('BASIC','ADVANCED'))
    choice.add_argument('--ratio',help='basic:advanced, for example 2:3')
    choice.add_argument('--basic-percent',help='basic percentage within 0..100')
    sub=commands.add_parser('revoke-review');sub.add_argument('id');sub.add_argument('--reason',required=True)
    args=parser.parse_args()
    try:
        if args.command=='mix':
            mode,value='default',None
            if args.counts is not None:mode,value='counts',args.counts
            elif args.ratio is not None:mode,value='ratio',args.ratio.split(':')
            elif args.basic_percent is not None:mode,value='percentage',args.basic_percent
            request={'mode':mode,'value':value,'basis':args.basis}
            result={**resolve_mix(args.count,request),'difficulty_request':request}
        elif args.command=='score':result=assess(read_json(args.input))
        elif args.command=='stats':
            bank=read_json(args.bank)
            result={'history_count':len(bank['exercises']),'review_count':len(bank['reviews']),
                    'eligible_reviews':sum(assess(r)['status']=='eligible' for r in bank['reviews'].values()),
                    'history_signature':history_signature(bank),
                    'implementation_languages':sorted(set().union(*(set(q.get('implementation_languages', [])) for q in bank['exercises']))),
                    'history_without_language':sum(not valid_languages(q.get('implementation_languages')) for q in bank['exercises']),
                    'coverage':{a:sorted(set().union(*(tagset(q,a) for q in bank['exercises']))) for a in AXES}}
        elif args.command=='check-plan':result=check_plan(read_json(args.input),read_json(args.bank),args.final)
        else:
            with edit_bank(args.bank) as bank:
                if args.command=='add-review':result=add_review(bank,read_json(args.input))
                elif args.command=='record-batch':result=record_batch(bank,read_json(args.input))
                else:
                    require(args.id in bank['reviews'],'review not found')
                    require(nonempty(args.reason),'revocation reason required')
                    bank['reviews'][args.id].update(revoked=True,revocation_reason=args.reason)
                    result={'status':'revoked','id':args.id}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 1 if result.get('status') in ('pending','rejected','blocked') else 0
    except (ValueError,TypeError,KeyError,OSError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
