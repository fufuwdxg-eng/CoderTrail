"""Bind agent-written homework annotations to every original line; never invent scores."""
import copy
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from curate_bank import WEIGHTS, nonempty, require
from execution_runner import canonical, digest, inside, verify_execution

LABELS = dict(correctness='正确性', readability='可读性与清晰度', maintainability='可维护性与可扩展性',
              testability='可测试性', performance='性能与效率', architecture='架构与设计质量',
              documentation='文档与可理解性', engineering='工程实践与规范', reliability='可靠性与健壮性')


def physical_lines(data, encoding):
    """Keep physical LF/CRLF/CR line numbers, not Unicode paragraph separators."""
    try:
        text = data.decode(encoding)
    except (LookupError, UnicodeError) as exc:
        raise ValueError('cannot decode submission with the declared encoding') from exc
    if '\0' in text:
        raise ValueError('binary file cannot be annotated as source')
    text = text.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    if not text:
        return []
    lines = text.split('\n')
    return lines[:-1] if text.endswith('\n') else lines


def source_catalog(execution, scope):
    run = verify_execution(execution)
    require(isinstance(scope, dict), 'homework scope must be an object')
    assignment = scope.get('assignment', {})
    require(isinstance(assignment, dict) and all(nonempty(assignment.get(k))
            for k in ('id', 'title', 'requirements', 'reference')), 'assignment identity and contract required')
    require(assignment.get('requirements_status') in ('complete', 'partial', 'unknown'),
            'assignment requirements_status required')
    included, excluded = scope.get('files'), scope.get('excluded_files', [])
    require(isinstance(included, list) and included and all(isinstance(x, dict) for x in included),
            'explicit student-authored files required')
    require(isinstance(excluded, list) and all(isinstance(x, dict) and nonempty(x.get('reason')) for x in excluded),
            'excluded files need reasons')
    names = [x.get('path') for x in included + excluded]
    require(all(nonempty(n) for n in names) and len(names) == len(set(names))
            and set(names) == set(run['files']), 'classify every snapshot file exactly once')
    catalog = {'contract': {'kind':'assignment', **assignment},
               'execution': {'kind':'execution', 'summary':run['summary']}}
    for i, step in enumerate(run['steps'], 1):
        for j, case in enumerate(step.get('tests', []), 1):
            catalog[f'test:{i}:{j}'] = {'kind':'test', 'step':step['id'], **case}
    lines = []
    snapshot = Path(execution).resolve().parent/'snapshot'
    for i, item in enumerate(included, 1):
        require(nonempty(item.get('encoding')), 'each file needs an explicit text encoding')
        for number, text in enumerate(physical_lines(inside(snapshot, item['path']).read_bytes(), item['encoding']), 1):
            ident = f'line:{i}:{number}'
            row = {'id':ident, 'path':item['path'], 'line':number, 'text':text}
            lines.append(row)
            catalog[ident] = {'kind':'source', **row}
    require(any(row['text'].strip() for row in lines), 'submission has no nonblank source lines')
    return run, lines, catalog


def prepare_homework(execution, scope):
    run, originals, catalog = source_catalog(execution, scope)
    lines = []
    for row in originals:
        blank = not row['text'].strip()
        lines.append({**row, 'kind':'blank' if blank else 'code',
            'status':'not_applicable' if blank else 'pending', 'score':None,
            'role':'空白行，用于分隔代码段。' if blank else '',
            'explanation':'不执行操作，不单独评价代码质量。' if blank else '',
            'score_reason':'空白行不参与评分。' if blank else '',
            'suggestion':'可保留该分隔。' if blank else '',
            'confidence':'high' if blank else 'unknown', 'evidence_ids':[row['id']],
            'issue_ids':[], 'suggested_code':None})
    return {'schema_version':1, 'kind':'learner_submission',
        'code_sha256':run['code_sha256'], 'execution_sha256':digest(Path(execution).read_bytes()),
        'scope':copy.deepcopy(scope), 'scope_sha256':digest(canonical(scope)),
        'reviewer':{'name':'', 'reviewed_at':''}, 'evidence_catalog':catalog,
        'scores':{key:{'rating':None, 'rationale':'', 'limitations':'', 'evidence_ids':[]} for key in WEIGHTS},
        'strengths':[], 'priority_actions':[], 'issues':[], 'lines':lines}


def check_homework(execution, review):
    require(isinstance(review, dict) and review.get('schema_version') == 1
            and review.get('kind') == 'learner_submission', 'unsupported homework review')
    run, originals, catalog = source_catalog(execution, review.get('scope'))
    require(review.get('code_sha256') == run['code_sha256']
            and review.get('execution_sha256') == digest(Path(execution).read_bytes()),
            'homework review belongs to a different submission or execution')
    require(review.get('scope_sha256') == digest(canonical(review['scope']))
            and review.get('evidence_catalog') == catalog, 'scope or evidence catalog changed')
    missing = []
    reviewer = review.get('reviewer', {})
    if not isinstance(reviewer, dict) or not nonempty(reviewer.get('name')):
        missing.append('reviewer name required')
    try:
        date.fromisoformat(reviewer.get('reviewed_at', ''))
    except (AttributeError, TypeError, ValueError):
        missing.append('review date required')

    def evidence(ids):
        return (isinstance(ids, list) and bool(ids)
                and all(isinstance(i, str) and i in catalog for i in ids))

    issues = review.get('issues')
    require(isinstance(issues, list), 'issues must be a list')
    by_issue = {}
    source_ids = {r['id'] for r in originals}
    for issue in issues:
        require(isinstance(issue, dict) and nonempty(issue.get('id')) and issue['id'] not in by_issue,
                'unique issue IDs required')
        require(issue.get('severity') in ('error', 'warning', 'suggestion')
                and issue.get('certainty') in ('confirmed', 'potential'), 'issue severity and certainty required')
        require(all(nonempty(issue.get(k)) for k in ('title','explanation','trigger','expected','observed','fix')),
                'issue needs cause, trigger, expected/observed behavior and a fix')
        require(evidence(issue.get('evidence_ids')), 'issue evidence reference unknown')
        refs = issue.get('affected_lines')
        require(isinstance(refs, list) and refs and all(isinstance(i,str) and i in source_ids for i in refs),
                'issue must reference actual source lines')
        by_issue[issue['id']] = issue
    rows = review.get('lines')
    require(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'line annotations required')
    by_line = {r.get('id'):r for r in rows if isinstance(r.get('id'), str)}
    require(len(by_line) == len(rows) == len(originals) and set(by_line) == source_ids,
            'every original line needs exactly one annotation; missing or duplicate lines')
    annotated = scored = uncertain = blanks = 0
    for original in originals:
        row = by_line[original['id']]
        require(all(row.get(k) == value for k, value in original.items()), 'original line identity or text changed')
        blank = not original['text'].strip()
        require(row.get('kind') in ('code','comment','structure','blank')
                and (row['kind'] == 'blank') == blank, 'nonblank lines cannot be excluded from grading')
        status, score = row.get('status'), row.get('score')
        require(status in ('correct','issue','uncertain','not_applicable','pending'), 'invalid line status')
        require((score is None or type(score) is int and 0 <= score <= 10), 'line score must be 0..10 or null')
        require((status == 'not_applicable') == blank, 'N/A is reserved for blank lines')
        require((status in ('correct','issue')) == (score is not None), 'line score and judgment disagree')
        require(row.get('confidence') in ('high','medium','low','unknown'), 'line confidence required')
        require(row.get('suggested_code') is None or isinstance(row['suggested_code'], str), 'suggested_code must be text or null')
        require(evidence(row.get('evidence_ids')), 'line evidence reference unknown')
        refs = row.get('issue_ids')
        require(isinstance(refs, list) and all(isinstance(i,str) and i in by_issue
                and row['id'] in by_issue[i]['affected_lines'] for i in refs), 'line issue references disagree')
        if status == 'issue':
            require(refs, 'problematic line must link to a shared issue explanation')
            require(any(by_issue[i]['certainty']=='confirmed' for i in refs),
                    'potential issue needs an uncertain judgment, not a definite deduction')
        expected_issues = {i for i, issue in by_issue.items() if row['id'] in issue['affected_lines']}
        require(set(refs) == expected_issues, 'all affected lines must link back to their shared issue')
        complete = status != 'pending' and row['confidence'] != 'unknown' and all(nonempty(row.get(k))
                   for k in ('role','explanation','score_reason','suggestion'))
        if not complete:
            missing.append(f'{row["path"]}:{row["line"]}: annotation unfinished')
        if status == 'uncertain':
            missing.append(f'{row["path"]}:{row["line"]}: judgment needs verification')
        annotated += complete
        scored += score is not None
        uncertain += status == 'uncertain'
        blanks += blank
    scores = review.get('scores', {})
    require(isinstance(scores,dict) and set(scores) == set(WEIGHTS), 'exactly nine quality dimensions required')
    total, rated = Decimal(0), True
    for key, weight in WEIGHTS.items():
        score = scores[key]
        require(isinstance(score,dict), 'quality score must be an object')
        rating = score.get('rating')
        require(rating is None or type(rating) is int and 0 <= rating <= 10, 'quality rating must be 0..10 or null')
        if rating is None:
            rated = False; missing.append(key+': unscored')
        else:
            total += Decimal(weight)*rating/10
        if not evidence(score.get('evidence_ids')) or not all(nonempty(score.get(k)) for k in ('rationale','limitations')):
            missing.append(key+': rationale, limitations or evidence missing')
    if review['scope']['assignment']['requirements_status'] != 'complete':
        require(scores['correctness']['rating'] is None, 'incomplete assignment cannot receive a correctness rating')
    for key in ('strengths','priority_actions'):
        require(isinstance(review.get(key),list) and all(nonempty(s) for s in review[key]), 'feedback must be a list of text')
    require(len(review['priority_actions']) <= 3, 'give at most three immediate priorities')
    if not review['priority_actions']:
        missing.append('next action required, including a consolidation task when no bug is found')
    return {'status':'complete' if not missing else 'partial', 'total':float(total) if rated else None,
            'missing':missing, 'weights':WEIGHTS, 'coverage':{'total_lines':len(originals),
            'annotated_lines':annotated, 'scored_lines':scored, 'blank_lines':blanks,
            'uncertain_lines':uncertain, 'files':len(review['scope']['files'])}, 'issue_count':len(issues)}


def fenced(text):
    marker = '`' * max(3, max((len(m) for m in re.findall(r'`+', text)), default=0)+1)
    return marker+'\n'+text+'\n'+marker


def render_homework(execution, review, base_report):
    result = check_homework(execution, review)
    report = copy.deepcopy(base_report)
    report.update(review_total=result['total'], scores=review['scores'], priority_actions=review['priority_actions'],
                  review_assessment={'status':result['status'], 'total':result['total'], 'missing':result['missing'],
                                     'failures':[], 'weights':WEIGHTS},
                  homework_review={'sha256':digest(canonical(review)), **result})
    report['rubric_version'] = 'nine-dim-v1-homework-1'
    if any(i['certainty']=='confirmed' and i['severity']=='error' for i in review['issues']):
        report['learner_status']='needs_revision'
    elif result['status']=='partial' and report['learner_status']!='needs_revision':
        report['learner_status']='needs_evidence'
    states = {'complete':'已完成', 'partial':'仍有待评项', 'passed':'通过', 'failed':'失败',
              'incomplete':'未完成', 'skipped':'跳过', 'correct':'正确', 'issue':'有问题',
              'uncertain':'待验证', 'not_applicable':'不计分', 'pending':'尚未批改'}
    confidences = {'high':'高', 'medium':'中', 'low':'低', 'unknown':'尚未判断'}

    def refs(ids):
        labels = []
        for ident in ids:
            item = review['evidence_catalog'][ident]
            if item['kind']=='source':label=f'{item["path"]} 第 {item["line"]} 行'
            elif item['kind']=='test':label=f'用例 {item["step"]}/{item["id"]}（{states[item["status"]]}）'
            elif item['kind']=='assignment':label='题目要求'
            else:label='本次执行记录'
            labels.append(label)
        return '；'.join(labels)

    title = review['scope']['assignment']['title']
    functional = report['functional_results']
    summary = ['# 作业批改报告', '', title, '', '九维总评沿用原权重；行分是教学诊断，不平均为总分。85 分是来源准入门槛，不淘汰低分作业。',
               f'九维总分：{result["total"] if result["total"] is not None else "待评"} / 100；批改状态：{states[result["status"]]}。',
               f'实际测试：{states[functional["status"]]}，通过 {functional["passed"]}、失败 {functional["failed"]}、跳过 {functional["skipped"]}。',
               f'逐行覆盖：{result["coverage"]["annotated_lines"]}/{result["coverage"]["total_lines"]}；其中 {result["coverage"]["blank_lines"]} 行为空白，不计分。逐行得分见 line-review.md。',
               '', '| 维度 | 权重 | 分数 0–10 | 理由与局限 |', '| --- | ---: | ---: | --- |']
    for key, weight in WEIGHTS.items():
        score = review['scores'][key]
        note = (score['rationale']+'；'+score['limitations']+'；依据：'+refs(score['evidence_ids'])).replace('|','/').replace('\n',' ')
        summary.append(f'| {LABELS[key]} | {weight} | {score["rating"] if score["rating"] is not None else "待评"} | {note} |')
    summary += ['', '## 做得好的地方', '']+['- '+s for s in review['strengths']]
    summary += ['', '## 优先修改与练习', '']+['- '+s for s in review['priority_actions']]
    summary += ['', '## 问题说明', '']
    for issue in review['issues']:
        severity={'error':'错误','warning':'需要注意','suggestion':'改进建议'}[issue['severity']]
        certainty={'confirmed':'已证实','potential':'待验证'}[issue['certainty']]
        summary += [f'### {issue["id"]} {issue["title"]}', '', f'程度：{severity}；确定性：{certainty}。',
                    '原因：'+issue['explanation'], '触发条件：'+issue['trigger'], '预期：'+issue['expected'],
                    '实际或推理结果：'+issue['observed'], '修改方向：'+issue['fix'],
                    '关联行：'+refs(issue['affected_lines']), '证据：'+refs(issue['evidence_ids']), '']
    if result['missing']:
        summary += ['## 尚待核实', '']+['- '+s for s in result['missing']]
    summary += ['', '修改建议尚不等于已验证修复；修正版必须另存并重跑相同验收。原始代码保持不变。', '']
    details = ['# 逐行批改', '', '行分 0–10；空白行为 N/A；缺少依据为待验证。共享问题只归因一次，不能按涉及行数重复扣总分。', '']
    rows = {row['id']:row for row in review['lines']}
    _, originals, _ = source_catalog(execution, review['scope'])
    current = None
    for original in originals:
        row = rows[original['id']]
        if row['path'] != current:
            current = row['path']; details += ['## '+current, '']
        score = str(row['score'])+' / 10' if row['score'] is not None else ('N/A（空白行）' if row['kind']=='blank' else '待验证')
        details += [f'### 第 {row["line"]} 行　{score}　{states[row["status"]]}', '', fenced(row['text']), '',
                    '- 作用：'+row['role'], '- 对错与原因：'+row['explanation'], '- 得分理由：'+row['score_reason'],
                    '- 修改建议：'+row['suggestion'], '- 判断把握：'+confidences[row['confidence']],
                    '- 证据：'+refs(row['evidence_ids'])]
        if row['issue_ids']:details.append('- 共享问题：'+', '.join(row['issue_ids']))
        if row.get('suggested_code') is not None:
            details += ['', '建议写法（未经执行不标为已修复）：', fenced(row['suggested_code'])]
        details.append('')
    if review['scope'].get('excluded_files'):
        details += ['## 未逐行评分的文件', '']+['- '+x['path']+'：'+x['reason'] for x in review['scope']['excluded_files']]
    return report, '\n'.join(summary), '\n'.join(details)
