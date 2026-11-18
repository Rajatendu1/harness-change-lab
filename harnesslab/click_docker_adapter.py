"""Separate fixed Click mapping, prepared only, no Docker execution performed.

Composition reuses reviewed keeper/image/resource/cleanup operations. The old
fictional fixture's accepted inputs and canned-only operation stay unchanged.
"""
from .click_task import BASE_NAMES, EDITABLE, validate_base
from .docker_fixture_adapter import DockerFixtureAdapter
from .source_bundle import MAX_ARCHIVE, unpack_sources


class ClickDockerAdapter:
    def __init__(self,*,image_policy,socket_directory,gateway_gid,runner=None):
        kwargs=dict(image_policy=image_policy,socket_directory=socket_directory,gateway_gid=gateway_gid)
        if runner is not None:kwargs['runner']=runner
        self.keeper=DockerFixtureAdapter(**kwargs)

    def create_keeper(self):return self.keeper.create_keeper()
    def verify_denials(self):return self.keeper.verify_denials()
    def stop_candidate(self):return self.keeper.stop_candidate()
    def observe(self):return self.keeper.observe()
    def remove_and_confirm_absent(self):return self.keeper.remove_and_confirm_absent()

    def _operation(self,operation,raw=None):
        if operation not in ('import','edit','export'):
            raise ValueError('Fixed Click operations only')
        args=['docker','exec']
        if operation=='import':args+=['-i']
        args+=['--user',f'65534:{self.keeper.gid}',self.keeper.name,
               'python3','-I','-m','harnesslab.click_editing_child',operation]
        return self.keeper.call(args,timeout=190 if operation=='edit' else 15,
                                max_bytes=MAX_ARCHIVE if operation=='export' else 1024,
                                input_data=raw)

    def import_click(self,raw,names):
        if tuple(names)!=BASE_NAMES:raise ValueError('Fixed base names required')
        validate_base(unpack_sources(raw,expected_names=BASE_NAMES))
        return self._operation('import',raw)

    def run_click_agent(self):return self._operation('edit')

    def export_click(self,names):
        if tuple(names)!=EDITABLE:raise ValueError('Fixed editable names required')
        return self._operation('export')
