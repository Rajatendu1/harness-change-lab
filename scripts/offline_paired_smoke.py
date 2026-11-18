#!/usr/bin/env python3
"""Two configuration/two task fixture workflow. No real models or providers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from harnesslab.experiment_journal import ExperimentJournal


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root',required=True)
    parser.add_argument('--output-directory',required=True,help='New directory, never overwritten')
    args=parser.parse_args()
    configurations={name:digest({'agent':'aider-0.86.2','canned_return':value})
                    for name,value in (('baseline',2),('candidate',1))}
    tasks={name:{'revision':digest({'base':'answer returns 0','scenario':name}),
                 'verifier_sha256':digest({'protected_test':test})}
           for name,test in (('fictional-repair','assert answer() == 1'),
                             ('broken-setup','deliberate collection error'))}
    journal=ExperimentJournal(args.output_directory, {
        'tasks':tasks,'configurations':configurations,'trials':1,'fixture_only':True,
        'execution_authority':'none','configuration_order':['baseline','candidate'],
        'policy':{'min_tasks':20,'margin':0.05,'confidence':0.95,'resamples':10000,'seed':0},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'child_script_sha256':hashlib.sha256(Path(__file__).with_name('offline_controller_smoke.py').read_bytes()).hexdigest(),
    })
    records=[]
    for task_id,identity in tasks.items():
        for configuration,value in (('baseline',2),('candidate',1)):
            command=[sys.executable,str(Path(__file__).with_name('offline_controller_smoke.py')),
                     '--runtime-root',args.runtime_root,'--fixture-return',str(value)]
            if task_id=='broken-setup': command.append('--broken-test-setup')
            result=subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=60)
            if result.returncode not in (0,1):
                raise RuntimeError('Offline fixture process failed before producing evidence')
            evidence=json.loads(result.stdout)
            execution=evidence['execution']
            outcome=evidence['score']['outcome']
            if execution['status']=='wall_clock_timeout': outcome='agent_timeout'
            elif execution['status']!='process_exited': outcome='agent_process_failure'
            elif execution['provider_pending_attempts'] or 'failed' in execution['provider_outcomes']:
                outcome='transport_failure'
            records.append({'configuration':configuration,'configuration_sha256':configurations[configuration],
                'task_id':task_id,'task_revision':identity['revision'],
                'verifier_sha256':identity['verifier_sha256'],'trial':0,'fixture_only':True,
                'outcome':outcome,'execution':execution,'score':evidence['score']})
            journal.append(records[-1])
    report=journal.finalize()
    print(json.dumps({'records':records,'report':report,'real_provider_calls':0,'real_model_repairs':0},
                     sort_keys=True,indent=2))
    return 0 if report['included_pairs']==1 and len(report['excluded_pairs'])==1 and report['verdict']=='insufficient_evidence' else 1


if __name__=='__main__':
    raise SystemExit(main())
