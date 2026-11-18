import copy
import unittest

from harnesslab.paired_controller import paired_report


class PairedControllerTests(unittest.TestCase):
    def setUp(self):
        self.configurations = {'baseline': 'a'*64, 'candidate': 'b'*64}
        self.tasks = {'fixture': {'revision': 'r1', 'verifier_sha256': 'c'*64}}
        self.rows = [dict(configuration=name, configuration_sha256=digest, task_id='fixture',
                          trial=0, task_revision='r1', verifier_sha256='c'*64,
                          fixture_only=True, outcome=outcome)
                     for (name,digest),outcome in zip(self.configurations.items(),
                                                     ('verifier_fail','source_patch_verifier_pass'))]

    def report(self, rows=None, **kwargs):
        args=dict(tasks=self.tasks,configurations=self.configurations,trials=1,fixture_only=True)
        args.update(kwargs)
        return paired_report(self.rows if rows is None else rows, **args)

    def test_valid_pairs_have_effect_but_fixture_never_clears_gate(self):
        result=self.report()
        self.assertEqual(result['included_pairs'],1)
        self.assertEqual(result['comparison']['delta'],1)
        self.assertEqual(result['verdict'],'insufficient_evidence')

    def test_setup_error_excludes_both_sides_not_false_failure(self):
        self.rows[0]['outcome']='verifier_setup_error'
        result=self.report()
        self.assertEqual(result['included_pairs'],0)
        self.assertIsNone(result['comparison'])
        self.assertEqual(result['excluded_pairs'][0]['outcomes']['baseline'],'verifier_setup_error')

    def test_missing_or_duplicate_rows_fail_closed(self):
        for rows in (self.rows[:1],self.rows+self.rows[:1]):
            with self.assertRaises(ValueError): self.report(rows)

    def test_identity_or_evidence_drift_is_rejected(self):
        for key,value in (('task_revision','r2'),('verifier_sha256','d'*64),
                          ('configuration_sha256','e'*64),('fixture_only',False),('trial',True)):
            rows=copy.deepcopy(self.rows); rows[0][key]=value
            with self.assertRaises(ValueError): self.report(rows)

    def test_no_edit_and_timeout_are_not_assertion_failures(self):
        for outcome in ('no_source_change','agent_timeout','transport_failure','invalid_patch'):
            self.rows[0]['outcome']=outcome
            self.assertEqual(self.report()['included_pairs'],0)

    def test_unknown_outcome_cannot_be_coerced(self):
        self.rows[0]['outcome']='success'
        with self.assertRaises(ValueError): self.report()


    def test_both_reference_classes_are_rejected_from_repair_metrics(self):
        for outcome in ('reference_verifier_pass','reference_verifier_fail'):
            self.rows[0]['outcome']=outcome
            with self.assertRaises(ValueError): self.report()
