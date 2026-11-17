"""A no-network mock-model integration check, NOT an agent benchmark.

Exercises the installed Inspect evaluation/log contract with fixed model responses.
It runs no shell tool, target repository, untrusted code, container or real model.
"""
from pathlib import Path
import json

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.log import read_eval_log
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import match
from inspect_ai.solver import generate


def main() -> None:
    output_dir = Path('local-evidence/mock-inspect')
    output_dir.mkdir(parents=True, exist_ok=True)
    model = get_model('mockllm/model', custom_outputs=lambda messages, *_: (
        ModelOutput.from_content('mockllm', 'fixed response' if
                                 messages[-1].text == 'fixture-pass' else 'wrong response')
    ))
    task = Task(
        name='synthetic-log-contract-only',
        dataset=[Sample(id='fixture-pass', input='fixture-pass', target='fixed response'),
                 Sample(id='fixture-fail', input='fixture-fail', target='fixed response')],
        solver=generate(), scorer=match(),
    )
    logs = eval(task, model=model, log_dir=str(output_dir),
                max_connections=1, display='none')
    if len(logs) != 1 or logs[0].status != 'success':
        raise RuntimeError('Mock contract check did not complete')
    log = read_eval_log(logs[0].location)
    samples = log.samples or []
    values = {str(s.id): list((s.scores or {}).values())[0].value for s in samples}
    if values != {'fixture-pass': 'C', 'fixture-fail': 'I'}:
        raise RuntimeError(f'Unexpected fixed-response grading: {values}')
    report = {
        'evidence_class': 'synthetic_mock_contract_only',
        'inspect_version': '0.3.290',
        'status': log.status,
        'sample_scores': values,
        'real_model_calls': 0,
        'sandbox_execution': False,
        'agent_benchmark': False,
        'log': str(Path(logs[0].location).resolve()),
    }
    (output_dir/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
