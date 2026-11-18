"""Model-free editing lifecycle controller with injected, fixed adapter operations.

No concrete Docker adapter exists here. Callbacks are trusted controller code,
not candidate instructions. Never wire a real provider into this fixture path.
"""
from .process_observation import ExportGate, KeeperIdentity
from .source_bundle import pack_sources, unpack_sources, overlay_candidate, validate_sources


class FixtureEditingSession:
    """Own cleanup in all branches; never score until removal is confirmed.

    Adapter contract:
      create_keeper() -> KeeperIdentity (independently read, not candidate output)
      import_base(raw, names) -> exact bytes marker
      run_canned_agent() -> exact bytes marker, uses one controller fixture budget
      stop_candidate() -> exact bytes marker
      observe() -> (bounded numeric top bytes, independent inspect state)
      export_sources(names) -> bounded archive bytes
      remove_and_confirm_absent() -> True, including partial create failure
    Each operation must enforce its own bounded IO/deadline. This orchestrator
    does not create those properties or supply execution authority by injection.
    """
    def __init__(self, adapter):
        self.adapter=adapter
        self._used=False

    def run(self, *, base, editable_names):
        if self._used:
            raise ValueError('Session cannot be reused or retried')
        self._used=True
        # Validate before any side effect. No remove needed for invalid inputs.
        validate_sources(base)
        names=tuple(editable_names)
        if len(names)!=len(set(names)):
            raise ValueError('Duplicate editable source names')
        # Reuse overlay validation to require exact existing editable files.
        overlay_candidate(base,{name:base[name] for name in names if name in base},editable_names=names)
        source_archive=pack_sources(base)
        stage='create'
        candidate=None
        failure=None
        try:
            identity=self.adapter.create_keeper()
            if not isinstance(identity,KeeperIdentity):
                raise ValueError('Keeper identity unverified')
            gate=ExportGate(identity)
            stage='denials'
            if hasattr(self.adapter,'verify_denials') and self.adapter.verify_denials()!=b'fixed-denials-ok\n':
                raise ValueError('Host denial fixture failed')
            stage='import'
            if self.adapter.import_base(source_archive,tuple(sorted(base)))!=b'source-import-ok\n':
                raise ValueError('Import unconfirmed')
            stage='canned_agent'
            if self.adapter.run_canned_agent()!=b'canned-agent-finished\n':
                raise ValueError('Canned agent incomplete')
            stage='candidate_cleanup'
            gate.candidate_cleanup_finished(self.adapter.stop_candidate())
            stage='observe'
            top,state=self.adapter.observe()
            gate.observe(top,state)
            stage='export'
            gate.consume_export()
            raw=self.adapter.export_sources(names)
            proposed=unpack_sources(raw,expected_names=names)
            candidate=overlay_candidate(base,proposed,editable_names=names)
        except Exception:
            # Never relay raw adapter errors, paths, archive data or candidate IO.
            failure=stage
        finally:
            try:
                removed=self.adapter.remove_and_confirm_absent() is True
            except Exception:
                removed=False
        if not removed:
            return {'status':'failed','stage':'container_cleanup','candidate':None,
                    'qualification_complete':False,'real_provider_calls':0}
        if failure:
            return {'status':'failed','stage':failure,'candidate':None,
                    'qualification_complete':False,'real_provider_calls':0}
        # Candidate stays private internal data. A future CLI must exclude this
        # field from logs/artifacts and pass it only into separate score/review.
        return {'status':'fixture_candidate_collected','stage':'complete','candidate':candidate,
                'qualification_complete':False,'real_provider_calls':0,
                'evidence':'injected_adapter_lifecycle_only'}
