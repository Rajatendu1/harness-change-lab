"""Prepared one-shot Click lifecycle. No execution CLI or authority implied.

Unlike the canned fixture, attempts are counted from an external lifetime
budget and never asserted to be zero. Candidate bytes stay controller-private.
The generic keeper mechanics are reused without changing the fixed fixture.
"""
from .click_task import BASE_NAMES, EDITABLE, validate_base
from .process_observation import ExportGate, KeeperIdentity
from .source_bundle import pack_sources, unpack_sources, overlay_candidate


class ClickEditingSession:
    def __init__(self,adapter,budget):
        self.adapter=adapter
        self.budget=budget
        self.used=False

    def run(self,base):
        if self.used:raise ValueError('One session, no reuse or retry')
        self.used=True
        validate_base(base)
        if self.budget.limit!=1 or self.budget.attempts!=0:
            raise ValueError('Fresh one-request budget required')
        candidate=None;stage='create';failure=None
        try:
            identity=self.adapter.create_keeper()
            if not isinstance(identity,KeeperIdentity):raise ValueError('Identity unverified')
            gate=ExportGate(identity)
            stage='denials'
            if self.adapter.verify_denials()!=b'fixed-denials-ok\n':raise ValueError('Denials unverified')
            stage='import'
            if self.adapter.import_click(pack_sources(base),BASE_NAMES)!=b'source-import-ok\n':
                raise ValueError('Import unconfirmed')
            stage='agent'
            if self.adapter.run_click_agent()!=b'click-agent-finished\n':raise ValueError('Agent incomplete')
            stage='request_audit'
            audit=self.budget.audit
            if (self.budget.attempts!=1 or len(audit)!=1 or audit[0].outcome!='returned'):
                raise ValueError('One returned request required')
            stage='candidate_cleanup'
            gate.candidate_cleanup_finished(self.adapter.stop_candidate())
            stage='observe'
            gate.observe(*self.adapter.observe())
            stage='export';gate.consume_export()
            edits=unpack_sources(self.adapter.export_click(EDITABLE),expected_names=EDITABLE)
            candidate=overlay_candidate(base,edits,editable_names=EDITABLE)
        except Exception:
            failure=stage
        finally:
            try:removed=self.adapter.remove_and_confirm_absent() is True
            except Exception:removed=False
        result={'status':'collected' if removed and failure is None else 'excluded',
                'stage':'complete' if removed and failure is None else (failure if removed else 'container_cleanup'),
                'provider_attempts':self.budget.attempts,
                'provider_outcomes':[row.outcome for row in self.budget.audit],
                'runtime_qualified':False,'adversarial_integrity_verified':False}
        # Only collection followed by confirmed removal may expose candidate to scorer.
        result['candidate']=candidate if result['status']=='collected' else None
        return result
