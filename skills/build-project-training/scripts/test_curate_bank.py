"""Synthetic regression cases. Never add these fixtures to the real catalog."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from functools import lru_cache
from pathlib import Path

from curate_bank import WEIGHTS, assess, add_review, check_plan, resolve_mix
from curate_bank import history_signature, read_json, record_batch
from curate_bank import reference_eligible
from execution_runner import run_project, execution_ref

_EVIDENCE = tempfile.TemporaryDirectory(prefix='curation-tests-')


@lru_cache(maxsize=32)
def collected_fixture(languages):
    """Actual Python processes with synthetic language labels; not ecosystem certification."""
    root=Path(_EVIDENCE.name); project=root/'project';project.mkdir(exist_ok=True)
    (project/'echo.py').write_text('import sys\nprint(sys.stdin.read().strip())\n')
    steps=[]
    for i,lang in enumerate(languages):
        steps.extend([{'id':f'version-{i}','role':'version','languages':[lang],'argv':['{python}','--version']},
          {'id':f'behavior-{i}','role':'test','languages':[lang],'argv':['{python}','echo.py'],'format':'cases',
           'cases':[{'id':'normal','category':'normal','stdin':'fixture','stdout':'fixture\n'},
                    {'id':'empty','category':'boundary','stdin':'','stdout':'\n'}]}])
    mode='single' if len(languages)==1 else 'collaboration'
    if mode=='collaboration':
        steps.append({'id':'integration','role':'integration','languages':list(languages),
                      'argv':['{python}','echo.py'],'format':'cases',
                      'cases':[{'id':'combined','category':'integration','stdin':'joined','stdout':'joined\n'}]})
    manifest={'schema_version':1,'project_id':'synthetic-control-fixture','languages':list(languages),
              'implementation_mode':mode,'files':['echo.py'],'steps':steps}
    out=root/('evidence-'+'-'.join(languages))
    result=run_project(manifest,project,out)
    return result,execution_ref(out/'execution.json','synthetic-test-archive')


def attach_execution(record):
    run,ref=collected_fixture(tuple(record['source']['languages']))
    record['source'].update(code_sha256=run['code_sha256'],implementation_mode=run['implementation_mode'])
    record['verification']['execution_refs']=[copy.deepcopy(ref)]
    return record


def review(ident='source-1',project='one',languages=('python',)):
    return attach_execution({'id':ident,'kind':'external_source','title':'Synthetic fixture',
        'reviewed_at':'2026-11-01',
        'source':{'url':f'https://example.invalid/{project}/fixed/code.py',
            'languages':list(languages),
            'project_url':f'https://example.invalid/{project}',
            'revision':'fixed-test-revision','code_sha256':'a'*64,
            'scope':'Synthetic function only; not an actual evaluated project',
            'evidence_archive_ref':'synthetic-fixture-only',
            'license':{'id':'TEST-ONLY','locator':'synthetic-license','reuse_allowed':True,
                       'obligations':'This is fictional test data; do not adopt.'}},
        'evidence':[{'id':'C','kind':'source','locator':'synthetic-code:1',
                     'observation':'Synthetic source inspection for test'},
                    {'id':'T','kind':'test','locator':'synthetic-test:1',
                     'observation':'Synthetic pass declaration for test'}],
        'scores':{k:{'rating':9,'evidence_ids':['C','T'],
                     'rationale':'Synthetic score rationale',
                     'limitations':'Only tests the gate; no actual project evaluated'} for k in WEIGHTS},
        'calibration':{'decision':'confirm','reviewer':'synthetic-rater','method':'blind-rerating',
                       'rationale':'Synthetic test case only','evidence_ids':['C']},
        'verification':{'code_inspected':True,'tests_executed':True,'tests_passed':True,
            'independent_checks':True,'critical_findings':[],
            'commands':['synthetic-test-command'],'environment':'synthetic-environment',
            'evidence_ids':['T'],
            'language_checks':[{'language':lang,'environment':'synthetic-environment',
                               'commands':['synthetic-runtime-test'],'evidence_ids':['T'],
                               'tests_passed':True} for lang in languages]}})


def empty_bank():
    return {'schema_version':2,'reviews':{},'exercises':[],'batches':[]}


def plan_fixture(n=5,languages=('python',)):
    bank=empty_bank();candidates=[];questions=[]
    for i in range(n):
        lang=languages[i%len(languages)]
        rid=f'source-{i}';r=review(rid,f'project-{i}',(lang,));add_review(bank,r)
        ref=review(f'impl-{i}',f'impl-{i}',(lang,))
        ref['kind']='reference_implementation';ref['parent_review_ids']=[rid]
        add_review(bank,ref)
        alternatives=[]
        for j in range(3):
            cid=rid if j==0 else f'alternative-{i}-{j}'
            project=r['source']['project_url'] if j==0 else f'https://example.invalid/alternative-{i}-{j}'
            alternatives.append(cid)
            candidates.append({'id':cid,'url':project+'/code','project_url':project,
                               'languages':[lang],
                               'scope':f'component-{i}-{j}','domain_tags':[f'domain-{i}'],
                               'disposition':'synthetic candidate'})
        questions.append({'id':f'new-q{i}','title':f'Synthetic question {i}',
            'task_type':'build','difficulty':{'modeling':1 if i==0 else 3,'algorithm':1,'design':2,'debugging':2,
                'rationale':'Synthetic calibrated workload','calibration_basis':'Synthetic baseline',
                'prerequisites':['synthetic basics'],'learning_goals':['synthetic objective'],'estimated_minutes':60},
            'implementation_languages':[lang],
            'level':'basic' if i==0 else 'advanced','domain_tags':[f'domain-{i}'],
            'concept_tags':[f'concept-{i}'],'artifact_tags':[f'artifact-{i}'],
            'engineering_tags':[f'practice-{i}'],'candidate_ids':alternatives,
            'source_review_ids':[rid],'reference_review_id':f'impl-{i}',
            'novelty_note':'Synthetic coverage only'})
    plan={'batch_id':'synthetic-batch','count':n,'basic_count':1,
          'scope_override_reason':'Explicit five-question synthetic test scenario',
          'language_context':{'mode':'single' if len(languages)==1 else 'mixed',
              'targets':list(languages),'selection_basis':'Explicit synthetic language request',
              'toolchains':[{'language':lang,'version':'synthetic-1.0',
                             'toolchain':'synthetic-toolchain','platform':'synthetic-platform'}
                            for lang in languages]},
          'history_signature':history_signature(bank),
          'research':{'history_checked':True,'completed_at':'2026-11-01T13:00:00+08:00',
                      'query_log':[{'query':'synthetic-query','date':'2026-11-01'}],
                      'candidates':candidates,'archive_ref':'synthetic-persistent-ref'},
          'questions':questions,'artifact':{'library_file_id':'synthetic-library-id'},
          'validation':dict.fromkeys(['all_code_executed','extracted_code_verified',
                                     'all_pages_reviewed','artifact_saved'],True)}
    return bank,plan


class GateTests(unittest.TestCase):
    def test_mix_default_and_all_explicit_fifteen_question_splits(self):
        self.assertEqual(resolve_mix(),{'count':15,'basic_count':3,'advanced_count':12,'rounding_applied':False})
        for basic in range(16):
            request={'mode':'counts','value':[basic,15-basic],'basis':'Synthetic explicit user request'}
            result=resolve_mix(15,request)
            self.assertEqual((result['basic_count'],result['advanced_count']),(basic,15-basic))

    def test_mix_ratios_percentages_and_rounding(self):
        for mode,value,expected,rounded in [('ratio',[2,3],6,False),('ratio',[1,1],8,True),
                ('percentage','40',6,False),('percentage','50',8,True),
                ('percentage','0',0,False),('percentage','100',15,False)]:
            result=resolve_mix(15,{'mode':mode,'value':value,'basis':'Synthetic explicit user request'})
            self.assertEqual(result['basic_count'],expected)
            self.assertEqual(result['advanced_count'],15-expected)
            self.assertEqual(result['rounding_applied'],rounded)

    def test_mix_invalid_requests_are_not_silently_adjusted(self):
        cases=[('counts',[5,11]),('counts',[5.5,9.5]),('counts',[True,14]),
               ('ratio',[0,0]),('ratio',[-1,2]),('ratio',['nan',1]),('ratio',['inf',1]),
               ('percentage',101),('percentage',-1),('percentage',True),('default',[3,12])]
        for mode,value in cases:
            with self.subTest(mode=mode,value=value),self.assertRaises(ValueError):
                resolve_mix(15,{'mode':mode,'value':value,'basis':'Synthetic request'})
        with self.assertRaises(ValueError):resolve_mix(15,{'mode':'counts','value':[5,10],'basis':''})

    def test_plan_custom_mix_and_saved_request(self):
        bank,plan=plan_fixture(15);plan.pop('scope_override_reason')
        for basic in (0,3,5,8,15):
            request={'mode':'counts','value':[basic,15-basic],'basis':'Synthetic user chooses this split'}
            plan.update(resolve_mix(15,request),difficulty_request=request)
            for i,q in enumerate(plan['questions']):
                q['level']='basic' if i<basic else 'advanced'
                q['difficulty']['modeling']=1 if i<basic else 3
            self.assertEqual(check_plan(plan,bank,True)['status'],'pass')
        record_batch(bank,plan)
        self.assertEqual(bank['batches'][0]['difficulty_mix']['advanced_count'],0)
        self.assertEqual(bank['batches'][0]['difficulty_request'],request)

    def test_plan_rejects_mix_mismatch_and_missing_basis(self):
        bank,plan=plan_fixture()
        plan['difficulty_request']={'mode':'counts','value':[1,4],'basis':'Synthetic request'}
        plan['advanced_count']=4
        self.assertEqual(check_plan(plan,bank)['status'],'pass')
        plan['advanced_count']=5
        self.assertEqual(check_plan(plan,bank)['status'],'blocked')
        plan['advanced_count']=4;plan['difficulty_request']['value']=[2,3]
        self.assertEqual(check_plan(plan,bank)['status'],'blocked')
        plan['difficulty_request'].update(value=[1,4],basis='')
        self.assertEqual(check_plan(plan,bank)['status'],'blocked')

    def test_mix_cli_reports_counts_without_bank_mutation(self):
        script=Path(__file__).with_name('curate_bank.py')
        command=[sys.executable,'-B',str(script),'--bank','/no-bank-needed','mix',
                 '--ratio','2:3','--basis','Synthetic request']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['basic_count'],6)
        result=subprocess.run([sys.executable,'-B',str(script),'mix','--counts','5','11',
                               '--basis','Synthetic request'],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)

    def test_weight_sum_and_exact_threshold(self):
        self.assertEqual(sum(WEIGHTS.values()),100)
        r=review();r['scores']['performance']['rating']=4
        self.assertEqual(assess(r)['total'],85)
        self.assertEqual(assess(r)['status'],'eligible')
    def test_no_rounding_up(self):
        r=review()
        for key,score in [('performance',6),('readability',8),('architecture',8)]:
            r['scores'][key]['rating']=score
        self.assertEqual(assess(r)['total'],84.5)
        self.assertEqual(assess(r)['status'],'rejected')
    def test_unknown_dimension_is_not_dropped(self):
        r=review();r['scores']['documentation']['rating']=None
        self.assertEqual(assess(r)['status'],'pending');self.assertIsNone(assess(r)['total'])
    def test_evidence_and_execution_required(self):
        for mutate in [lambda r:r['scores']['architecture'].update(evidence_ids=['missing']),
                       lambda r:r['verification'].update(tests_executed=False),
                       lambda r:r['verification'].update(independent_checks=False),
                       lambda r:r['source']['license'].update(reuse_allowed=None),
                       lambda r:r['source'].update(revision='main')]:
            r=review();mutate(r);self.assertNotEqual(assess(r)['status'],'eligible')
    def test_critical_findings_and_failed_tests(self):
        for change in [{'tests_passed':False},{'critical_findings':['data loss']}]:
            r=review();r['verification'].update(change)
            self.assertEqual(assess(r)['status'],'rejected')
    def test_dimension_floor(self):
        r=review();r['scores']['correctness']['rating']=8
        self.assertGreaterEqual(assess(r)['total'],85)
        self.assertEqual(assess(r)['status'],'rejected')
    def test_bool_and_invalid_rating(self):
        for value in [True,11,-1,8.5,'9']:
            r=review();r['scores']['correctness']['rating']=value
            with self.assertRaises(ValueError):assess(r)
    def test_add_is_idempotent_and_never_upgrades_pending(self):
        bank=empty_bank();r=review();add_review(bank,r);add_review(bank,r)
        self.assertEqual(len(bank['reviews']),1)
        r['scores']['readability']['rating']=10
        with self.assertRaises(ValueError):add_review(bank,r)
        r=review('pending');r['verification']['tests_executed']=False
        with self.assertRaises(ValueError):add_review(bank,r)
        self.assertEqual(len(bank['reviews']),1)
    def test_reference_requires_qualified_parent(self):
        r=review();r['kind']='reference_implementation'
        r['parent_review_ids']=['absent']
        with self.assertRaises(ValueError):add_review(empty_bank(),r)
    def test_valid_plan_and_final_record(self):
        bank,plan=plan_fixture()
        self.assertEqual(check_plan(plan,bank,True)['status'],'pass')
        record_batch(bank,plan)
        self.assertEqual(len(bank['exercises']),5)
        self.assertEqual(len(bank['batches']),1)
        with self.assertRaises(ValueError):record_batch(bank,plan)
    def test_count_balance_and_missing_research(self):
        for mutate in [lambda p:p.update(basic_count=3),
                       lambda p:p.update(scope_override_reason=''),
                       lambda p:p['research'].update(candidates=[]),
                       lambda p:p['research'].update(query_log=[]),
                       lambda p:p.update(history_signature='stale')]:
            bank,p=plan_fixture();mutate(p)
            self.assertEqual(check_plan(p,bank)['status'],'blocked')
    def test_renamed_history_repetition_and_within_batch(self):
        bank,p=plan_fixture();old=copy.deepcopy(p['questions'][0])
        old.update(id='historic',title='Old different title');bank['exercises'].append(old)
        p['history_signature']=history_signature(bank)
        p['questions'][0].update(title='New skin',domain_tags=['new-skin'],artifact_tags=['different-output'])
        self.assertTrue(any('repeats historic' in x for x in check_plan(p,bank)['issues']))
        bank,p=plan_fixture();p['questions'][1]['concept_tags']=p['questions'][0]['concept_tags']
        p['questions'][1]['engineering_tags']=p['questions'][0]['engineering_tags']
        self.assertTrue(any('repeats new-q0' in x for x in check_plan(p,bank)['issues']))
    def test_source_revocation_and_missing_final_review(self):
        bank,p=plan_fixture();bank['reviews']['source-0']['revoked']=True
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
        bank,p=plan_fixture();p['questions'][0]['reference_review_id']='absent'
        self.assertEqual(check_plan(p,bank)['status'],'pass')
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
    def test_candidate_repo_mismatch(self):
        bank,p=plan_fixture()
        p['research']['candidates'][0]['project_url']='https://example.invalid/different'
        self.assertTrue(any('disagree' in x for x in check_plan(p,bank)['issues']))
    def test_no_record_without_saved_artifact_and_qa(self):
        for mutate in [lambda p:p.update(artifact={}),
                       lambda p:p['validation'].update(extracted_code_verified=False),
                       lambda p:p['research'].update(archive_ref='')]:
            bank,p=plan_fixture();before=copy.deepcopy(bank);mutate(p)
            with self.assertRaises(ValueError):record_batch(bank,p)
            self.assertEqual(bank,before)
    def test_cli_atomic_rejection_and_success(self):
        script=Path(__file__).with_name('curate_bank.py')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);bankpath=root/'bank.json';recordpath=root/'review.json'
            bankpath.write_text(json.dumps(empty_bank()))
            bad=review();bad['scores']['correctness']['rating']=0
            recordpath.write_text(json.dumps(bad));before=bankpath.read_bytes()
            command=[sys.executable,str(script),'--bank',str(bankpath),'add-review',str(recordpath)]
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(bankpath.read_bytes(),before)
            recordpath.write_text(json.dumps(review()))
            result=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(read_json(bankpath)['reviews']),1)

    def test_language_does_not_change_scores_or_threshold(self):
        expected={'correctness':20,'readability':10,'maintainability':10,'testability':10,
                  'performance':10,'architecture':15,'documentation':5,'engineering':10,'reliability':10}
        self.assertEqual(WEIGHTS,expected)
        for lang in ('python','javascript','typescript','c','cpp','java','csharp','go','rust','sql','bash','swift'):
            with self.subTest(language=lang):
                r=review(languages=(lang,))
                self.assertEqual(assess(r)['total'],90)
                r['scores']['performance']['rating']=4
                self.assertEqual(assess(r)['status'],'eligible')
                r['scores']['documentation']['rating']=8
                self.assertEqual(assess(r)['total'],84.5)
                self.assertEqual(assess(r)['status'],'rejected')

    def test_each_language_needs_actual_execution_declaration(self):
        for mutate in [lambda r:r['source'].pop('languages'),
                       lambda r:r['source'].update(languages=['go','go']),
                       lambda r:r['verification'].pop('language_checks'),
                       lambda r:r['verification']['language_checks'][0].update(language='python'),
                       lambda r:r['verification']['language_checks'][0].update(evidence_ids=['C']),
                       lambda r:r['verification']['language_checks'][0].update(commands=[]),
                       lambda r:r['verification']['language_checks'][0].update(tests_passed=None)]:
            r=review(languages=('go','typescript'));mutate(r)
            self.assertEqual(assess(r)['status'],'pending')
        r=review(languages=('go','typescript'))
        r['verification']['language_checks'][1]['tests_passed']=False
        self.assertEqual(assess(r)['status'],'rejected')

    def test_single_and_mixed_language_delivery_preserves_metadata(self):
        for languages in [('cpp',),('java',),('go','typescript'),('rust','python','csharp')]:
            with self.subTest(languages=languages):
                bank,p=plan_fixture(languages=languages)
                self.assertEqual(check_plan(p,bank,True)['status'],'pass')
                record_batch(bank,p)
                self.assertEqual(bank['batches'][0]['language_context'],p['language_context'])
                self.assertEqual({x for q in bank['exercises'] for x in q['implementation_languages']},set(languages))

    def test_incomplete_or_inconsistent_language_plan_is_blocked(self):
        mutations=[lambda p:p.pop('language_context'),
                   lambda p:p['language_context'].update(mode='single'),
                   lambda p:p['language_context'].update(selection_basis=''),
                   lambda p:p['language_context'].update(toolchains=[]),
                   lambda p:p['language_context']['toolchains'][0].update(version='latest'),
                   lambda p:p['questions'][0].update(implementation_languages=[]),
                   lambda p:p['questions'][0].update(implementation_languages=['cpp']),
                   lambda p:p['research']['candidates'][0].update(languages=[])]
        for mutate in mutations:
            bank,p=plan_fixture(languages=('go','typescript'));mutate(p)
            self.assertEqual(check_plan(p,bank)['status'],'blocked')

    def test_every_selected_language_must_be_used(self):
        bank,p=plan_fixture(languages=('go',))
        p['language_context']['mode']='mixed'
        p['language_context']['targets'].append('rust')
        p['language_context']['toolchains'].append(dict(language='rust',version='synthetic-1.0',
                                                        toolchain='synthetic',platform='synthetic'))
        self.assertIn('question implementations must cover exactly the selected languages',
                      check_plan(p,bank)['issues'])

    def test_different_final_language_cannot_substitute(self):
        bank,p=plan_fixture(languages=('rust',))
        ref=bank['reviews']['impl-0']
        ref['source']['languages']=['python']
        ref['verification']['language_checks'][0]['language']='python'
        attach_execution(ref)
        self.assertEqual(assess(ref)['status'],'eligible')
        self.assertEqual(check_plan(p,bank)['status'],'pass')
        self.assertTrue(any('languages do not match' in x for x in check_plan(p,bank,True)['issues']))

    def test_cross_language_source_needs_explicit_adaptation(self):
        bank,p=plan_fixture(languages=('cpp',))
        source=bank['reviews']['source-0']
        source['source']['languages']=['python']
        source['verification']['language_checks'][0]['language']='python'
        attach_execution(source)
        p['research']['candidates'][0]['languages']=['python']
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
        p['questions'][0]['cross_language_adaptations']=[{
            'source_review_id':'source-0','target_languages':['cpp'],
            'semantic_risks':'Synthetic: integer width and ownership semantics',
            'verification_plan':'Synthetic: independent boundary and lifetime tests'}]
        self.assertEqual(check_plan(p,bank,True)['status'],'pass')
        p['questions'][0]['cross_language_adaptations'][0]['target_languages']=['go']
        self.assertEqual(check_plan(p,bank)['status'],'blocked')

    def test_changing_only_language_never_creates_novelty(self):
        bank,p=plan_fixture(languages=('go',))
        old=copy.deepcopy(p['questions'][0])
        old.update(id='old-python',implementation_languages=['python'])
        bank['exercises'].append(old);p['history_signature']=history_signature(bank)
        self.assertIn('new-q0: repeats old-python',check_plan(p,bank)['issues'])

    def test_multi_language_reference_requires_all_runtime_evidence(self):
        bank,p=plan_fixture(languages=('go','typescript'))
        q=p['questions'][0];q['implementation_languages']=['go','typescript']
        q['source_language_targets']={'source-0':['go','typescript']}
        q['cross_language_adaptations']=[{'source_review_id':'source-0','target_languages':['typescript'],
            'semantic_risks':'Synthetic interface semantics','verification_plan':'Synthetic contract tests'}]
        ref=bank['reviews']['impl-0'];ref['source']['languages']=['go','typescript']
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
        ref['verification']['language_checks'].append({'language':'typescript','environment':'synthetic',
            'commands':['synthetic-runtime-test'],'evidence_ids':['T'],'tests_passed':True})
        attach_execution(ref)
        self.assertEqual(check_plan(p,bank,True)['status'],'pass')

    def test_multilingual_components_use_their_own_sources(self):
        bank,p=plan_fixture(languages=('go','typescript'))
        q=p['questions'][0];q['implementation_languages']=['go','typescript']
        rid='extra-ts';source=review(rid,'extra-ts-project',('typescript',));add_review(bank,source)
        candidate=p['research']['candidates'][1]
        candidate.update(id=rid,url=source['source']['url'],project_url=source['source']['project_url'],
                         languages=['typescript'])
        q['candidate_ids'][1]=rid;q['source_review_ids'].append(rid)
        q['source_language_targets']={'source-0':['go'],rid:['typescript']}
        ref=bank['reviews']['impl-0'];ref['source']['languages']=['go','typescript']
        ref['parent_review_ids'].append(rid)
        ref['verification']['language_checks'].append({'language':'typescript','environment':'synthetic',
            'commands':['synthetic-runtime-test'],'evidence_ids':['T'],'tests_passed':True})
        attach_execution(ref)
        self.assertEqual(check_plan(p,bank,True)['status'],'pass')
        del q['source_language_targets']
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
        q['source_language_targets']={'source-0':['go'],rid:['go']}
        self.assertEqual(check_plan(p,bank)['status'],'blocked')

    def test_declarations_alone_never_admit(self):
        r=review();r['verification'].pop('execution_refs')
        self.assertEqual(assess(r)['status'],'pending')

    def test_wrong_source_hash_and_severe_dimension_block(self):
        r=review();r['source']['code_sha256']='0'*64
        self.assertEqual(assess(r)['status'],'rejected')
        r=review()
        for score in r['scores'].values():score['rating']=10
        r['scores']['architecture']['rating']=0
        self.assertEqual(assess(r)['total'],85)
        self.assertEqual(assess(r)['status'],'rejected')

    def test_borderline_needs_recalibration(self):
        r=review();r['scores']['performance']['rating']=4;r.pop('calibration')
        self.assertEqual(assess(r)['status'],'pending')

    def test_reviewed_combinations_count_as_substantive_breadth(self):
        bank,p=plan_fixture()
        for i in range(5):
            old=copy.deepcopy(p['questions'][i]);old.update(id=f'old-{i}',
                domain_tags=[f'domain-{(i+2)%5}'],artifact_tags=[f'artifact-{(i+3)%5}'],
                engineering_tags=[f'practice-{(i+1)%5}'])
            bank['exercises'].append(old)
        p['history_signature']=history_signature(bank)
        self.assertEqual(check_plan(p,bank)['status'],'blocked')
        for i,q in enumerate(p['questions']):
            q['novelty_evidence']={'kind':'combination','compared_ids':[f'old-{i}'],
                'axes':['concept_tags','engineering_tags'],'delta':'Synthetic new combination',
                'acceptance':'Synthetic observable new requirement',
                'review':{'approved':True,'reviewer':'synthetic-reviewer','evidence_ref':'synthetic-only'}}
        self.assertEqual(check_plan(p,bank)['status'],'pass')
        for q in p['questions']:q['novelty_evidence']['review']['approved']=False
        self.assertEqual(check_plan(p,bank)['status'],'blocked')

    def test_difficulty_cannot_be_a_label_only(self):
        bank,p=plan_fixture();p['questions'][0]['difficulty']['design']=4
        self.assertEqual(check_plan(p,bank)['status'],'blocked')
        bank,p=plan_fixture();p['questions'][1].pop('difficulty')
        self.assertEqual(check_plan(p,bank)['status'],'blocked')

    def test_reference_rechecks_parent_eligibility(self):
        bank,p=plan_fixture();ref=bank['reviews']['impl-0']
        self.assertTrue(reference_eligible(ref,bank))
        bank['reviews']['source-0']['revoked']=True
        self.assertFalse(reference_eligible(ref,bank))
        self.assertEqual(check_plan(p,bank,True)['status'],'blocked')
        bank['reviews']['source-0']['revoked']=False
        ref['parent_review_ids']=[]
        self.assertFalse(reference_eligible(ref,bank))

    def test_variants_need_independent_eligible_reviews(self):
        bank=empty_bank();parent=review('parent',languages=('python','javascript'));add_review(bank,parent)
        children={}
        for lang in ('python','javascript'):
            child=review('child-'+lang,languages=(lang,));child['kind']='reference_implementation'
            child['parent_review_ids']=['parent'];add_review(bank,child);children[lang]=child['id']
        ref=review('variant-total',languages=('python','javascript'))
        ref['kind']='reference_implementation';ref['parent_review_ids']=['parent']
        root=Path(_EVIDENCE.name)
        manifest=read_json(root/'evidence-python-javascript/manifest.json');manifest['implementation_mode']='variants'
        out=root/'variants-only'
        run_project(manifest,root/'project',out)
        ref['source']['implementation_mode']='variants'
        ref['verification']['execution_refs']=[execution_ref(out/'execution.json','synthetic-only')]
        self.assertFalse(reference_eligible(ref,bank))
        ref['variant_review_ids']=children
        self.assertTrue(reference_eligible(ref,bank))
        bank['reviews']['child-javascript']['revoked']=True
        self.assertFalse(reference_eligible(ref,bank))

if __name__=='__main__':
    unittest.main(verbosity=2)
