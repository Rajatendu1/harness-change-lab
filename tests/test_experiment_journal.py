import copy
import json
from pathlib import Path
import tempfile
import unittest

from harnesslab.experiment_journal import ExperimentJournal


class ExperimentJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name)/'experiment'
        self.plan={'tasks':{'fixture':{'revision':'r1','verifier_sha256':'c'*64}},
                   'configurations':{'baseline':'a'*64,'candidate':'b'*64},
                   'trials':1,'fixture_only':True,'execution_authority':'none','configuration_order':['baseline','candidate'],
                   'policy':{'min_tasks':20,'margin':0.05,'confidence':0.95,'resamples':100,'seed':0}}
        self.records=[{'task_id':'fixture','task_revision':'r1','verifier_sha256':'c'*64,
                       'configuration':name,'configuration_sha256':digest,'trial':0,'fixture_only':True,
                       'outcome':'verifier_fail'} for name,digest in self.plan['configurations'].items()]

    def test_plan_precedes_flushed_records_and_report_references_both(self):
        journal=ExperimentJournal(self.directory,self.plan)
        self.assertTrue((self.directory/'plan.json').exists())
        self.assertEqual((self.directory/'records.jsonl').read_text(),'')
        for row in self.records: journal.append(row)
        report=journal.finalize()
        self.assertEqual(report['plan_sha256'],journal.plan_hash)
        self.assertEqual(len(report['records_sha256']),64)
        self.assertEqual(report['verdict'],'insufficient_evidence')
        with self.assertRaises(ValueError): journal.append(self.records[0])

    def test_partial_run_stays_visible_but_has_no_final_report(self):
        journal=ExperimentJournal(self.directory,self.plan)
        journal.append(self.records[0])
        with self.assertRaises(ValueError): journal.finalize()
        self.assertFalse((self.directory/'report.json').exists())
        self.assertEqual(len((self.directory/'records.jsonl').read_text().splitlines()),1)

    def test_plan_changed_after_start_is_refused(self):
        journal=ExperimentJournal(self.directory,self.plan)
        changed=copy.deepcopy(self.plan); changed['policy']['min_tasks']=2
        (self.directory/'plan.json').write_text(json.dumps({'plan':changed,'plan_sha256':journal.plan_hash}))
        with self.assertRaises(ValueError): journal.append(self.records[0])

    def test_record_changed_without_consistent_digest_is_refused(self):
        journal=ExperimentJournal(self.directory,self.plan)
        for row in self.records: journal.append(row)
        path=self.directory/'records.jsonl'
        path.write_text(path.read_text().replace('verifier_fail','source_patch_verifier_pass',1))
        with self.assertRaises(ValueError): journal.finalize()

    def test_existing_directory_never_overwritten(self):
        ExperimentJournal(self.directory,self.plan)
        with self.assertRaises(FileExistsError): ExperimentJournal(self.directory,self.plan)


    def test_policy_is_checked_before_first_child(self):
        self.plan['policy']['min_tasks']=1
        with self.assertRaises(ValueError): ExperimentJournal(self.directory,self.plan)
        self.assertFalse((self.directory/'report.json').exists())


    def test_saved_review_recomputes_report_without_execution(self):
        from harnesslab.journal_review import read_journal, summary
        journal=ExperimentJournal(self.directory,self.plan)
        for row in self.records: journal.append(row)
        journal.finalize()
        plan, records, report=read_journal(self.directory)
        self.assertEqual(report['roles'],{'baseline':'baseline','candidate':'candidate'})
        self.assertIn('Pairs: 1 included / 1 planned',summary(self.directory))
        path=self.directory/'report.json'
        changed=json.loads(path.read_text()); changed['verdict']='no_detected_regression'
        path.write_text(json.dumps(changed))
        with self.assertRaises(ValueError): read_journal(self.directory)

    def test_config_role_order_survives_sorted_json(self):
        from harnesslab.journal_review import read_journal
        self.plan['configuration_order']=['candidate','baseline']
        self.records[0]['outcome']='verifier_fail'
        self.records[1]['outcome']='source_patch_verifier_pass'
        journal=ExperimentJournal(self.directory,self.plan)
        for row in self.records: journal.append(row)
        journal.finalize()
        _,_,report=read_journal(self.directory)
        self.assertEqual(report['roles']['baseline'],'candidate')
        self.assertEqual(report['comparison']['delta'],-1)
