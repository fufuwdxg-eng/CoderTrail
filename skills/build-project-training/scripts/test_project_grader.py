"""Actual subprocess checks. Curated source quality is not inferred from these fixtures."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from execution_runner import run_project, verify_execution, load_json, write_json, execution_ref, digest
from project_grader import make_report, prepare_review, package_sources, record_attempt
from curate_bank import assess

SKILL = Path(__file__).resolve().parents[1]
FIXTURES = SKILL/'assets/validation-fixtures'


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='grader-tests-')
        self.root = Path(self.temp.name)
        self.project = self.root/'project';self.project.mkdir()
        self.counter=0

    def tearDown(self):
        self.temp.cleanup()

    def run_code(self, code, cases=None, *, junit=False):
        (self.project/'main.py').write_text(code)
        manifest={'schema_version':1,'project_id':'actual-test-fixture','languages':['python'],
            'implementation_mode':'single','files':['main.py'],'steps':[
                {'id':'version','role':'version','languages':['python'],'argv':['{python}','--version']},
                {'id':'behavior','role':'test','languages':['python'],'argv':['{python}','main.py'],
                 'format':'cases','cases':cases or [{'id':'one','category':'normal','stdin':'','stdout':'OK\n'}]}]}
        if junit:
            manifest['steps'][-1].update(format='junit',result_file='results.xml',category='normal')
            manifest['steps'][-1].pop('cases')
        return self.run_manifest(manifest,self.project)

    def run_manifest(self, manifest, project):
        self.counter+=1
        out=self.root/f'evidence-{self.counter}'
        run=run_project(manifest,project,out)
        self.assertEqual(verify_execution(out/'execution.json')['summary'],run['summary'])
        return run,out

    def test_native_python_javascript_cpp(self):
        for lang,command in [('python','python3'),('javascript','node'),('cpp','g++')]:
            with self.subTest(language=lang):
                if not shutil.which(command):
                    self.skipTest(f'{command} unavailable; cannot certify that runtime')
                run,out=self.run_manifest(load_json(FIXTURES/f'manifest-{lang}.json'),FIXTURES)
                self.assertEqual(run['summary']['status'],'passed')
                self.assertEqual(run['summary']['executed'],12)
                report,md=make_report(out/'execution.json')
                self.assertIsNone(report['review_total'])
                self.assertEqual(report['admission_status'],'not_applicable')
                self.assertIn('待评',md)

    def test_actual_python_javascript_integration(self):
        if not shutil.which('node'):self.skipTest('Node.js unavailable')
        manifest=load_json(FIXTURES/'manifest-collaboration.json')
        run,out=self.run_manifest(manifest,FIXTURES)
        self.assertTrue(run['summary']['integration_passed'])
        self.assertEqual(run['summary']['executed'],36)
        manifest['steps']=[s for s in manifest['steps'] if s['role']!='integration']
        with self.assertRaises(ValueError):run_project(manifest,FIXTURES,self.root/'missing-integration')

    def test_wrong_answer_is_measured(self):
        run,out=self.run_code('print("WRONG")\n')
        self.assertEqual(run['summary']['status'],'failed')
        self.assertEqual(run['summary']['failed'],1)
        report,md=make_report(out/'execution.json')
        self.assertEqual(report['learner_status'],'needs_revision')
        self.assertIn('behavior/one',md)

    def test_missing_runtime_is_incomplete(self):
        manifest=load_json(FIXTURES/'manifest-python.json')
        manifest['steps'][0]['argv']=['nonexistent-training-runtime-9140']
        run,_=self.run_manifest(manifest,FIXTURES)
        self.assertEqual(run['summary']['status'],'incomplete')
        self.assertEqual(run['summary']['executed'],0)

    def test_timeout_cannot_pass(self):
        (self.project/'main.py').write_text('import time\ntime.sleep(5)\n')
        manifest=load_json(FIXTURES/'manifest-python.json')
        manifest['files']=['main.py'];manifest['steps'][-1].update(argv=['{python}','main.py'],timeout_seconds=.1)
        manifest['steps'][-1]['cases']=manifest['steps'][-1]['cases'][:1]
        run,_=self.run_manifest(manifest,self.project)
        self.assertNotEqual(run['summary']['status'],'passed')
        self.assertEqual(run['steps'][-1]['invocations'][0]['error'],'timeout')

    def test_zero_tests_and_skipped_tests_are_incomplete(self):
        for xml in ['<testsuite tests="99"/>','<testsuite><testcase name="one"><skipped/></testcase></testsuite>']:
            run,_=self.run_code('from pathlib import Path\nPath("results.xml").write_text('+repr(xml)+')\n',junit=True)
            self.assertEqual(run['summary']['status'],'incomplete')

    def test_junit_counts_cases_not_claimed_totals(self):
        xml='<testsuite tests="999" failures="0"><testcase name="a"/><testcase name="b"><failure>wrong</failure></testcase></testsuite>'
        run,_=self.run_code('from pathlib import Path\nPath("results.xml").write_text('+repr(xml)+')\n',junit=True)
        self.assertEqual(run['summary']['executed'],2)
        self.assertEqual(run['summary']['failed'],1)
        self.assertEqual(run['summary']['status'],'failed')

    def test_successful_junit_requires_successful_process(self):
        xml='<testsuite><testcase name="a"/><testcase name="b"/></testsuite>'
        code='from pathlib import Path\nPath("results.xml").write_text('+repr(xml)+')\n'
        run,_=self.run_code(code,junit=True)
        self.assertEqual(run['summary']['status'],'passed')
        run,_=self.run_code(code+'raise SystemExit(1)\n',junit=True)
        self.assertEqual(run['summary']['status'],'failed')

    def test_output_is_exact_utf8_bytes(self):
        run,_=self.run_code('import sys\nsys.stdout.buffer.write(b"\\xff")\n',
            cases=[{'id':'encoding','category':'boundary','stdin':'','stdout':'\ufffd'}])
        self.assertEqual(run['summary']['status'],'failed')

    def test_stale_junit_is_removed(self):
        (self.project/'main.py').write_text('pass\n')
        (self.project/'results.xml').write_text('<testsuite><testcase name="stale"/></testsuite>')
        manifest={'schema_version':1,'project_id':'stale','languages':['python'],'implementation_mode':'single',
                  'files':['main.py','results.xml'],'steps':[
                      {'id':'version','role':'version','languages':['python'],'argv':['{python}','--version']},
                      {'id':'tests','role':'test','languages':['python'],'argv':['{python}','main.py'],
                       'format':'junit','result_file':'results.xml','category':'normal'}]}
        run,_=self.run_manifest(manifest,self.project)
        self.assertEqual(run['summary']['executed'],0)
        self.assertNotEqual(run['summary']['status'],'passed')

    def test_xml_entities_not_accepted(self):
        xml='<!DOCTYPE x [<!ENTITY e "unsafe">]><testsuite><testcase name="&e;"/></testsuite>'
        run,_=self.run_code('from pathlib import Path\nPath("results.xml").write_text('+repr(xml)+')\n',junit=True)
        self.assertEqual(run['summary']['status'],'incomplete')

    def test_changed_source_fails(self):
        run,_=self.run_code('from pathlib import Path\nPath("main.py").write_text("changed")\nprint("OK")\n')
        self.assertFalse(run['source_unchanged'])
        self.assertEqual(run['summary']['status'],'failed')

    def test_tampered_logs_snapshot_and_report_are_detected(self):
        for target in ('log','snapshot','report'):
            run,out=self.run_code('print("OK")\n')
            ref=execution_ref(out/'execution.json','test archive')
            if target=='log':(out/run['steps'][-1]['invocations'][0]['stdout']).write_text('changed')
            elif target=='snapshot':(out/'snapshot/main.py').write_text('changed')
            else:
                run['summary']['passed']=99;write_json(out/'execution.json',run)
            with self.assertRaises(ValueError):verify_execution(out/'execution.json',ref['sha256'])

    def test_failed_build_cannot_be_declared_passed(self):
        run,out=self.run_code('print("OK")\n')
        run['steps'][0]['invocations'][0]['exit_code']=1
        write_json(out/'execution.json',run)
        with self.assertRaises(ValueError):verify_execution(out/'execution.json')

    def test_snapshot_escape_and_symlink_rejected(self):
        manifest=load_json(FIXTURES/'manifest-python.json')
        manifest['files']=['../outside.py']
        with self.assertRaises(ValueError):run_project(manifest,FIXTURES,self.root/'escape')
        (self.project/'link.py').symlink_to(FIXTURES/'python/sum_cli.py')
        manifest['files']=['link.py']
        with self.assertRaises(ValueError):run_project(manifest,self.project,self.root/'symlink')

    def test_prepare_review_does_not_invent_quality(self):
        run,out=self.run_code('print("OK")\n')
        review=prepare_review(out/'execution.json','test archive',load_json(SKILL/'assets/review-template.json'))
        review['id']='test-review'
        self.assertTrue(review['verification']['tests_executed'])
        self.assertFalse(review['verification']['code_inspected'])
        self.assertTrue(all(s['rating'] is None for s in review['scores'].values()))
        self.assertEqual(assess(review)['status'],'pending')
        source=prepare_review(out/'execution.json','test archive',load_json(SKILL/'assets/review-template.json'),'external_source')
        self.assertEqual(source['kind'],'external_source')
        self.assertTrue(all(s['rating'] is None for s in source['scores'].values()))

    def test_learning_keeps_failure_and_compares_same_contract(self):
        history=self.root/'history.json';write_json(history,{'schema_version':1,'attempts':[]})
        for attempt,code in [('first','print("WRONG")\n'),('second','print("OK")\n')]:
            _,out=self.run_code(code)
            report,_=make_report(out/'execution.json');path=self.root/(attempt+'.json');write_json(path,report)
            item=record_attempt(history,path,{'attempt_id':attempt,'question_id':'q1','minutes_spent':10,'hints_used':0})
        data=load_json(history)
        self.assertEqual(len(data['attempts']),2)
        self.assertEqual(data['attempts'][0]['functional_results']['failed'],1)
        self.assertEqual(item['comparison']['passed_delta'],1)
        with self.assertRaises(ValueError):record_attempt(history,path,{'attempt_id':'second','question_id':'q1'})
        report['functional_results']['passed']=999;write_json(path,report)
        with self.assertRaises(ValueError):record_attempt(history,path,{'attempt_id':'forged-count','question_id':'q1'})

    def test_admission_requires_parents_and_preserves_rejection(self):
        from test_curate_bank import review, empty_bank
        source=review('parent-for-grader')
        child=copy.deepcopy(source);child.update(id='child-for-grader',kind='reference_implementation',parent_review_ids=[source['id']])
        execution=child['verification']['execution_refs'][0]['local_path']
        bank=empty_bank();bank['reviews'][source['id']]=source
        report,_=make_report(execution,child,'admission',bank)
        self.assertEqual(report['admission_status'],'eligible')
        report,_=make_report(execution,child,'admission')
        self.assertEqual(report['admission_status'],'pending')
        source['revoked']=True
        report,_=make_report(execution,child,'admission',bank)
        self.assertEqual(report['admission_status'],'pending')
        child['scores']['performance']['rating']=0
        report,_=make_report(execution,child,'admission',bank)
        self.assertEqual(report['admission_status'],'rejected')

    def test_source_package_uses_verified_snapshot(self):
        run,out=self.run_code('print("OK")\n')
        package=package_sources(out/'execution.json',self.root/'source.zip')
        self.assertEqual(package['code_sha256'],run['code_sha256'])
        self.assertTrue(Path(package['path']).is_file())
        unpacked=self.root/'unpacked'
        with zipfile.ZipFile(package['path']) as archive:archive.extractall(unpacked)
        grader=unpacked/'_training_tools/scripts/project_grader.py'
        replay=self.root/'package-evidence'
        command=[sys.executable,'-B',str(grader),'run',str(unpacked/'training-manifest.json'),
                 '--project',str(unpacked),'--out',str(replay)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'passed')
        result=subprocess.run([sys.executable,'-B',str(grader),'prepare-review',str(replay/'execution.json'),
            '--archive-ref','test-only','--kind','external_source','--out',str(self.root/'draft.json')],
            capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(load_json(self.root/'draft.json')['kind'],'external_source')


if __name__=='__main__':
    unittest.main(verbosity=2)
