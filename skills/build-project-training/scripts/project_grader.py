#!/usr/bin/env python3
"""Run project tests, bind evidence, report nine-dimension reviews and learning progress."""
import argparse
import copy
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from execution_runner import (run_project, verify_execution, execution_ref, load_json,
                              write_json, digest, inside)
from curate_bank import WEIGHTS, assess, reference_eligible, edit_bank
from homework_review import LABELS, prepare_homework, check_homework, render_homework


def prepare_review(execution, archive_ref, template, kind='reference_implementation'):
    run = verify_execution(execution)
    review = copy.deepcopy(template)
    if kind not in ('external_source', 'reference_implementation'):
        raise ValueError('invalid review kind')
    review.update(kind=kind, reviewed_at=datetime.now(timezone.utc).date().isoformat())
    review['source'].update(code_sha256=run['code_sha256'], languages=run['languages'],
                            implementation_mode=run['implementation_mode'], evidence_archive_ref=archive_ref)
    ident = 'execution-'+digest(Path(execution).read_bytes())[:16]
    review.setdefault('evidence', []).append({'id': ident, 'kind': 'test', 'locator': archive_ref,
                                            'observation': json.dumps(run['summary'], ensure_ascii=False)})
    commands = [' '.join(r['argv']) for s in run['steps'] for r in s['invocations']]
    review['verification'].update(tests_executed=run['summary']['executed'] > 0,
        tests_passed=True if run['summary']['status']=='passed' else (False if run['summary']['status']=='failed' else None),
        commands=commands, environment=run['platform'], evidence_ids=[ident],
        execution_refs=[execution_ref(execution, archive_ref)],
        language_checks=[{'language': lang, 'environment':run['platform'],
            'commands':[' '.join(r['argv']) for s in run['steps'] if lang in s['languages'] for r in s['invocations']],
            'evidence_ids':[ident], 'tests_passed':run['summary']['status']=='passed'} for lang in run['languages']])
    # Code inspection, independent-check judgment, license and all nine ratings remain unfilled.
    return review


def make_report(execution, review=None, purpose='learner', bank=None):
    run = verify_execution(execution)
    assessment = None
    if review:
        if review.get('source', {}).get('code_sha256') != run['code_sha256']:
            raise ValueError('review refers to different code; re-review this snapshot')
        hashes = {r.get('sha256') for r in review.get('verification', {}).get('execution_refs', [])}
        if digest(Path(execution).read_bytes()) not in hashes:
            raise ValueError('review does not reference this exact execution report')
        assessment = assess(review)
        if review.get('kind') == 'reference_implementation' and (not bank or not reference_eligible(review, bank)):
            assessment = {**assessment,
                'status':'rejected' if assessment['status']=='rejected' else 'pending',
                'missing':assessment['missing']+['qualified parent sources and required variant reviews are not verified']}
    summary = run['summary']
    diagnostic = 'needs_revision' if summary['status']=='failed' else ('needs_evidence' if summary['status']=='incomplete' else 'tests_passed')
    result = {'schema_version':1, 'purpose':purpose, 'created_at':datetime.now(timezone.utc).isoformat(),
        'project_id':run['project_id'], 'code_sha256':run['code_sha256'],
        'manifest_sha256':run['manifest_sha256'], 'languages':run['languages'], 'rubric_version':'nine-dim-v1',
        'execution_ref':execution_ref(execution, str(Path(execution).resolve())),
        'functional_results':summary, 'review_total':assessment['total'] if assessment else None,
        'admission_status':assessment['status'] if purpose=='admission' and assessment else ('pending' if purpose=='admission' else 'not_applicable'),
        'learner_status':diagnostic if purpose=='learner' else None,
        'review_assessment':assessment, 'scores':review.get('scores', {}) if review else {}}
    actions=[]
    for step in run['steps']:
        for case in step.get('tests',[]):
            if case['status']!='passed':actions.append(f'先处理 {step["id"]}/{case["id"]}：对照输入、预期输出和实际日志。')
        if step.get('incomplete'):actions.append(f'补齐 {step["id"]} 的环境或有效执行证据。')
    rated=[(k,v) for k,v in result['scores'].items() if type(v.get('rating')) is int]
    for key,value in sorted(rated,key=lambda item:item[1]['rating']):
        if value['rating']<9:actions.append(f'改进{LABELS[key]}：{value.get("rationale", "查看对应审阅证据")}')
    if not assessment:actions.append('完成九维代码审阅后再判断整体代码质量。')
    result['priority_actions']=list(dict.fromkeys(actions))[:3]
    lines = ['# 项目评分报告', '', f'项目：{run["project_id"]}',
             f'用途：{"学习诊断（不按 85 分淘汰练习）" if purpose=="learner" else "来源/参考实现准入"}', '',
             f'实际运行：{summary["status"]}；通过 {summary["passed"]}，失败 {summary["failed"]}，跳过 {summary["skipped"]}。',
             '测试通过比例仅描述本验收集，不替代九维质量分，也不证明任意输入正确。', '',
             '| 维度 | 权重 | 审阅分（0–10） | 判断理由、局限与证据 |', '| --- | ---: | ---: | --- |']
    for key, weight in WEIGHTS.items():
        score = result['scores'].get(key, {})
        rating = score.get('rating')
        reason = (score.get('rationale', '')+'；'+score.get('limitations', '')).strip('；') or '待代码审阅及证据核验'
        if score.get('evidence_ids'):reason+='；证据：'+', '.join(score['evidence_ids'])
        lines.append(f'| {LABELS[key]} | {weight} | {rating if rating is not None else "待评"} | {reason.replace(chr(10), " ").replace("|", "/")} |')
    lines += ['', f'九维审阅总分：{result["review_total"] if result["review_total"] is not None else "待评，不重新归一化"}。',
              f'准入状态：{result["admission_status"]}。', '', '## 具体反馈', '']
    lines += ['- '+action for action in result['priority_actions']]
    lines += ['', f'执行档案：{Path(execution).resolve()}', '']
    for step in run['steps']:
        for test in step.get('tests', []):
            if test['status'] != 'passed':
                lines.append(f'- {step["id"]}/{test["id"]}：{test["status"]}；对照该步骤日志和验收合同定位差异。')
        for invocation in step['invocations']:
            if invocation['error']:
                lines.append(f'- {step["id"]}：{invocation["error"]}；先解决环境、超时或输出限制。')
    if assessment:
        lines += ['- '+msg for msg in assessment['failures']+assessment['missing']]
    else:
        lines.append('- 尚未提交九维审阅记录；测试结果不会自动填成九项高分。')
    lines += ['', '证据采用文件摘要与日志一致性检查，不是数字签名；无法证明执行者未伪造材料。',
              '运行器不是恶意代码安全沙箱。需先审查代码和命令，并在适当隔离的执行环境运行。', '']
    return result, '\n'.join(lines)


def record_attempt(history_path, report_path, observation):
    report = load_json(report_path)
    if report.get('purpose') != 'learner':
        raise ValueError('only learner diagnostics belong in learning history')
    ref=report.get('execution_ref',{})
    run=verify_execution(ref.get('local_path',''),ref.get('sha256'))
    if (any(report.get(k)!=run[k] for k in ('code_sha256','manifest_sha256','languages'))
            or report.get('functional_results')!=run['summary']):
        raise ValueError('learning report differs from captured execution')
    if not observation.get('attempt_id') or not observation.get('question_id'):
        raise ValueError('attempt_id and question_id required')
    for field in ('minutes_spent', 'hints_used'):
        value = observation.get(field)
        if value is not None and (type(value) not in (int,float) or value < 0):
            raise ValueError(f'{field} must be nonnegative or null')
    if observation.get('independently_completed') is not None and type(observation['independently_completed']) is not bool:
        raise ValueError('independently_completed must be boolean or null')
    path = Path(history_path)
    if not path.exists():
        raise ValueError('initialize history from learning-history.json template first')
    with edit_bank(path) as history:
        attempts = history.setdefault('attempts', [])
        if any(x['attempt_id']==observation['attempt_id'] for x in attempts):
            raise ValueError('attempt already recorded; preserve original attempt')
        item = {**observation, 'created_at':report['created_at'], 'report_path':str(Path(report_path).resolve()),
                'report_sha256':digest(Path(report_path).read_bytes()),
                'code_sha256':report['code_sha256'], 'manifest_sha256':report['manifest_sha256'],
                'languages':report['languages'], 'rubric_version':report['rubric_version'],
                'functional_results':report['functional_results'], 'review_total':report['review_total']}
        comparable = [a for a in attempts if all(a.get(k)==item.get(k) for k in ('question_id','manifest_sha256','languages','rubric_version'))]
        item['comparison'] = {'previous_attempt_id':comparable[-1]['attempt_id'],
            'passed_delta':item['functional_results']['passed']-comparable[-1]['functional_results']['passed']} if comparable else None
        if comparable and item['review_total'] is not None and comparable[-1]['review_total'] is not None:
            item['comparison']['review_total_delta'] = item['review_total']-comparable[-1]['review_total']
        attempts.append(item)
    return item


def package_sources(execution, output):
    run = verify_execution(execution); root=Path(execution).resolve().parent
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in run['files']:
            z.write(inside(root/'snapshot', name), name)
        z.write(root/'manifest.json', 'training-manifest.json')
        skill=Path(__file__).resolve().parents[1]
        for rel in ('scripts/project_grader.py','scripts/execution_runner.py','scripts/curate_bank.py','scripts/homework_review.py',
                    'assets/review-template.json','assets/learning-history.json','assets/learning-observation-template.json',
                    'assets/homework-scope-template.json','references/homework-marking.md',
                    'references/scoring-program.md','references/quality-rubric.md','references/language-adaptation.md'):
            if rel=='assets/learning-history.json':
                z.writestr('_training_tools/'+rel,json.dumps({'schema_version':1,'attempts':[]}))
            else:z.write(skill/rel,'_training_tools/'+rel)
    return {'path':str(Path(output).resolve()), 'code_sha256':run['code_sha256'], 'files':len(run['files'])}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('manifest');run.add_argument('--project',required=True);run.add_argument('--out',required=True)
    verify=sub.add_parser('verify');verify.add_argument('execution')
    prep=sub.add_parser('prepare-review');prep.add_argument('execution');prep.add_argument('--archive-ref',required=True)
    prep.add_argument('--template',default=str(Path(__file__).resolve().parents[1]/'assets/review-template.json'));prep.add_argument('--out',required=True)
    prep.add_argument('--kind',choices=['external_source','reference_implementation'],default='reference_implementation')
    hw=sub.add_parser('prepare-homework');hw.add_argument('execution');hw.add_argument('--scope',required=True);hw.add_argument('--out',required=True)
    check=sub.add_parser('check-homework');check.add_argument('execution');check.add_argument('--review',required=True)
    hwgrade=sub.add_parser('review-homework');hwgrade.add_argument('execution');hwgrade.add_argument('--review',required=True);hwgrade.add_argument('--out',required=True)
    grade=sub.add_parser('grade');grade.add_argument('execution');grade.add_argument('--review');grade.add_argument('--bank')
    grade.add_argument('--purpose',choices=['learner','admission'],default='learner');grade.add_argument('--out',required=True)
    attempt=sub.add_parser('record-attempt');attempt.add_argument('report');attempt.add_argument('--observation',required=True);attempt.add_argument('--history',required=True)
    pack=sub.add_parser('package');pack.add_argument('execution');pack.add_argument('--out',required=True)
    args=parser.parse_args()
    try:
        if args.command=='run':
            report=run_project(load_json(args.manifest),args.project,args.out); result=report['summary']
        elif args.command=='verify':result=verify_execution(args.execution)['summary']
        elif args.command=='prepare-review':
            if Path(args.out).exists():raise ValueError('review output exists')
            write_json(args.out,prepare_review(args.execution,args.archive_ref,load_json(args.template),args.kind))
            result={'status':'draft','path':args.out}
        elif args.command=='prepare-homework':
            if Path(args.out).exists():raise ValueError('homework review output exists')
            write_json(args.out,prepare_homework(args.execution,load_json(args.scope)))
            result={'status':'draft','path':args.out}
        elif args.command=='check-homework':
            result=check_homework(args.execution,load_json(args.review))
        elif args.command=='review-homework':
            review=load_json(args.review);base,_=make_report(args.execution,purpose='learner')
            report,markdown,lines=render_homework(args.execution,review,base)
            out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
            write_json(out/'grade.json',report);write_json(out/'homework-review.json',review)
            (out/'grade.md').write_text(markdown,encoding='utf-8')
            (out/'line-review.md').write_text(lines,encoding='utf-8')
            result={'path':str(out),'status':report['homework_review']['status'],
                    'review_total':report['review_total'],'coverage':report['homework_review']['coverage']}
        elif args.command=='grade':
            out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
            report,markdown=make_report(args.execution,load_json(args.review) if args.review else None,args.purpose,load_json(args.bank) if args.bank else None)
            write_json(out/'grade.json',report);(out/'grade.md').write_text(markdown,encoding='utf-8')
            result={'path':str(out),'admission_status':report['admission_status'],'learner_status':report['learner_status'],'review_total':report['review_total']}
        elif args.command=='record-attempt':result=record_attempt(args.history,args.report,load_json(args.observation))
        else:result=package_sources(args.execution,args.out)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 1 if result.get('status') in ('failed','incomplete','partial') or result.get('admission_status') in ('pending','rejected') else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False),file=sys.stderr);return 2


if __name__=='__main__':
    sys.exit(main())
