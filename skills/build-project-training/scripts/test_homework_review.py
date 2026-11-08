"""Synthetic grading records test the workflow, never certify or enter the source bank."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from execution_runner import run_project, write_json, load_json, digest
from homework_review import prepare_homework, check_homework, render_homework, physical_lines, fenced
from project_grader import make_report, record_attempt


class HomeworkTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='homework-tests-')
        self.root=Path(self.temp.name);self.project=self.root/'project';self.project.mkdir()
        self.code='# 学生平均数作业\nimport json\nimport sys\n\nvalues = json.loads(sys.stdin.read())\ntotal = sum(values)\nprint(total / len(values))\n'
        (self.project/'main.py').write_text(self.code,encoding='utf-8')
        (self.project/'teacher.txt').write_text('Synthetic teacher contract, not student code.')
        self.manifest={'schema_version':1,'project_id':'homework-fixture','languages':['python'],
            'implementation_mode':'single','files':['main.py','teacher.txt'],'steps':[
                {'id':'version','role':'version','languages':['python'],'argv':['{python}','--version']},
                {'id':'behavior','role':'test','languages':['python'],'argv':['{python}','main.py'],'format':'cases',
                 'cases':[{'id':'normal','category':'normal','stdin':'[2,4]','stdout':'3.0\n'},
                          {'id':'empty','category':'boundary','stdin':'[]','stdout':'0.0\n'}]}]}
        self.out=self.root/'evidence';run_project(self.manifest,self.project,self.out)
        self.execution=self.out/'execution.json'
        self.scope={'assignment':{'id':'test-mean','title':'Synthetic mean task','requirements':'Average JSON list; empty returns 0.0.',
                    'reference':'Synthetic teacher contract','requirements_status':'complete'},
                    'files':[{'path':'main.py','encoding':'utf-8'}],
                    'excluded_files':[{'path':'teacher.txt','reason':'Synthetic teacher-supplied text'}]}

    def tearDown(self):
        self.temp.cleanup()

    def completed(self):
        review=prepare_homework(self.execution,self.scope)
        review['reviewer']={'name':'synthetic-workflow-test','reviewed_at':'2026-11-02'}
        review['strengths']=['Synthetic explanatory text, not an actual student evaluation.']
        review['priority_actions']=['Handle the empty input case, then rerun the contract.']
        for score in review['scores'].values():
            score.update(rating=8,rationale='Synthetic rubric test',limitations='Not a real quality certification',evidence_ids=['contract','execution'])
        review['scores']['correctness']['rating']=6
        review['scores']['reliability']['rating']=5
        for row in review['lines']:
            if row['kind']=='blank':continue
            row.update(status='correct',score=9,role='Synthetic contextual role',explanation='Synthetic explanation',
                       score_reason='Synthetic score rationale',suggestion='Retain this line.',confidence='high')
        last=review['lines'][-1]
        last.update(status='issue',score=4,issue_ids=['empty-division'],suggestion='Handle empty values before division.',
                    suggested_code='print(total / len(values) if values else 0.0)')
        review['issues']=[{'id':'empty-division','title':'Empty input division', 'severity':'error','certainty':'confirmed',
            'explanation':'The divisor becomes zero.', 'trigger':'[]', 'expected':'0.0', 'observed':'Captured ZeroDivisionError',
            'fix':'Handle the empty case before dividing.', 'affected_lines':[last['id']], 'evidence_ids':[last['id'],'test:2:2']}]
        return review

    def test_draft_preserves_every_line_and_never_invents_scores(self):
        review=prepare_homework(self.execution,self.scope)
        self.assertEqual([r['text'] for r in review['lines']],self.code.splitlines())
        self.assertEqual([r['line'] for r in review['lines']],list(range(1,8)))
        self.assertTrue(all(r['score'] is None for r in review['lines']))
        self.assertTrue(all(r['rating'] is None for r in review['scores'].values()))
        self.assertEqual(check_homework(self.execution,review)['status'],'partial')

    def test_failed_low_score_homework_receives_complete_feedback(self):
        review=self.completed();result=check_homework(self.execution,review)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['total'],73)
        self.assertEqual(result['coverage'],{'total_lines':7,'annotated_lines':7,'scored_lines':6,
                        'blank_lines':1,'uncertain_lines':0,'files':1})
        base,_=make_report(self.execution)
        report,summary,lines=render_homework(self.execution,review,base)
        self.assertEqual(report['admission_status'],'not_applicable')
        self.assertEqual(report['learner_status'],'needs_revision')
        self.assertEqual(report['review_total'],73)
        self.assertIn('73.0',summary);self.assertIn('第 7 行',lines);self.assertIn('ZeroDivisionError',summary)
        for label in ('作用','对错与原因','得分理由','修改建议'):self.assertIn(label,lines)

    def test_missing_duplicate_and_changed_original_lines_are_rejected(self):
        for variant in ('missing','duplicate','changed'):
            review=self.completed()
            if variant=='missing':review['lines'].pop(0)
            elif variant=='duplicate':review['lines'].append(copy.deepcopy(review['lines'][0]))
            else:review['lines'][0]['text']='changed'
            with self.assertRaises(ValueError):check_homework(self.execution,review)

    def test_nonblank_lines_cannot_be_hidden_as_na(self):
        review=self.completed();review['lines'][0].update(kind='blank',status='not_applicable',score=None)
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review=self.completed();review['lines'][0]['score']=True
        with self.assertRaises(ValueError):check_homework(self.execution,review)

    def test_pending_unknown_and_potential_issues_are_not_definite_deductions(self):
        review=self.completed();review['issues'][0]['certainty']='potential'
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review['lines'][-1].update(status='uncertain',score=None,confidence='low')
        review['scores']['correctness']['rating']=None
        result=check_homework(self.execution,review)
        self.assertEqual(result['status'],'partial');self.assertIsNone(result['total'])
        self.assertEqual(result['coverage']['uncertain_lines'],1)

    def test_incomplete_contract_cannot_be_assigned_correctness(self):
        self.scope['assignment']['requirements_status']='unknown'
        review=self.completed()
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review['scores']['correctness']['rating']=None
        self.assertIsNone(check_homework(self.execution,review)['total'])

    def test_shared_issue_links_and_evidence_are_checked(self):
        review=self.completed();review['lines'][-1]['issue_ids']=[]
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review=self.completed();review['lines'][0]['evidence_ids']=['invented']
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review=self.completed();review['issues'][0]['affected_lines'].append(review['lines'][-2]['id'])
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review['lines'][-2]['issue_ids']=['empty-division']
        self.assertEqual(check_homework(self.execution,review)['issue_count'],1)

    def test_scope_and_execution_binding_are_required(self):
        scope=copy.deepcopy(self.scope);scope['excluded_files']=[]
        with self.assertRaises(ValueError):prepare_homework(self.execution,scope)
        review=self.completed();review['execution_sha256']='0'*64
        with self.assertRaises(ValueError):check_homework(self.execution,review)
        review=self.completed();review['evidence_catalog']['execution']['summary']['passed']=999
        with self.assertRaises(ValueError):check_homework(self.execution,review)

    def test_line_numbering_handles_windows_bom_and_unicode(self):
        self.assertEqual(physical_lines('\ufeff甲\r\n\r\n乙\u2028丙\n'.encode(),'utf-8'),['甲','','乙\u2028丙'])
        self.assertEqual(physical_lines(b'','utf-8'),[])
        with self.assertRaises(ValueError):physical_lines(b'\xff','utf-8')
        self.assertTrue(fenced('```\ncode').startswith('````\n'))

    def test_cli_reports_and_learning_history_preserve_original_submission(self):
        original=digest((self.project/'main.py').read_bytes());path=self.root/'review.json'
        write_json(path,self.completed())
        script=Path(__file__).with_name('project_grader.py');out=self.root/'feedback'
        result=subprocess.run([sys.executable,'-B',str(script),'review-homework',str(self.execution),
             '--review',str(path),'--out',str(out)],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        for name in ('grade.json','grade.md','line-review.md','homework-review.json'):self.assertTrue((out/name).is_file())
        self.assertEqual(digest((self.project/'main.py').read_bytes()),original)
        history=self.root/'history.json';write_json(history,{'schema_version':1,'attempts':[]})
        item=record_attempt(history,out/'grade.json',{'attempt_id':'synthetic-1','question_id':'test-mean'})
        self.assertEqual(item['review_total'],73)
        self.assertEqual(item['functional_results']['failed'],1)


if __name__=='__main__':
    unittest.main(verbosity=2)
