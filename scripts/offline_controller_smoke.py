#!/usr/bin/env python3
"""Run actual Aider with a canned completion, then a separate protected test.

Synthetic adapter evidence only. No real provider, credentials or model. Requires
an installed harnesslab plus locally provisioned agent/verifier directories.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from harnesslab.isolated_trial import isolated_trial
from harnesslab.protected_score import score_candidate
from harnesslab.request_budget import TrialRequestBudget


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-root', required=True)
    parser.add_argument('--fixture-return', type=int, choices=(1, 2), default=1)
    parser.add_argument('--broken-test-setup', action='store_true')
    args = parser.parse_args()
    runtime = Path(args.runtime_root).resolve(strict=True)
    agent, verifier = runtime / 'agent', runtime / 'verifier'
    with tempfile.TemporaryDirectory(prefix='offline-controller-smoke-') as directory:
        root = Path(directory)
        candidate, base, hidden = (root / name for name in ('candidate', 'base', 'hidden'))
        for path in (candidate, base, hidden):
            path.mkdir()
        source = 'def answer():\n    return 0\n'
        (candidate / 'example.py').write_text(source)
        (base / 'example.py').write_text(source)
        (hidden / 'test_hidden.py').write_text(
            'import sys\nsys.path.insert(0,"/work")\nfrom example import answer\ndef test_answer(): assert answer()==1\n')
        for command in (['git', 'init', '-q'], ['git', 'add', 'example.py'],
                        ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture']):
            subprocess.run(command, cwd=candidate, check=True, stdin=subprocess.DEVNULL)
        if args.broken_test_setup:
            (hidden / 'test_hidden.py').write_text('raise RuntimeError("deliberate fixture collection failure")\n')
        def canned(body):
            # Controller-created response, not an inference result.
            return json.dumps({'id': 'fixture', 'object': 'chat.completion', 'created': 0,
                'model': 'fixture-model', 'choices': [{'index': 0, 'finish_reason': 'stop',
                'message': {'role': 'assistant', 'content': 'example.py\n```python\ndef answer():\n    return %s\n```' % args.fixture_return}}],
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}).encode()
        budget = TrialRequestBudget(1, canned)
        command = [str(agent / 'bin' / 'python'), '-m', 'aider.main', '--model', 'openai/fixture-model',
            '--no-stream', '--no-analytics', '--no-check-update', '--no-gitignore', '--no-auto-commits',
            '--no-dirty-commits', '--no-auto-lint', '--no-auto-test', '--no-suggest-shell-commands',
            '--no-show-model-warnings', '--map-tokens', '0', '--edit-format', 'whole', '--yes-always',
            '--message', 'Change answer to return 1. Edit example.py only.', 'example.py']
        execution = isolated_trial(command, workspace=candidate, budget=budget, model='fixture-model',
                                   max_output_tokens=256, timeout_s=20, read_only_paths=[agent])
        # Explicit controller cleanup of known Aider bookkeeping only.
        for path in candidate.glob('.aider*'):
            if path.is_file() and not path.is_symlink():
                path.unlink()
        score = score_candidate(base=base, candidate=candidate, editable_files=['example.py'],
                                protected_tests=hidden, python=verifier / 'bin' / 'python', runtime_root=verifier)
        passed = (execution.status == 'process_exited' and execution.provider_attempts == 1
                  and not execution.provider_pending_attempts and score.outcome == 'source_patch_verifier_pass'
                  and score.tests == 1)
        print(json.dumps({'schema': 'offline-controller-smoke-v0', 'fixture_only': True,
                          'real_provider_calls': 0, 'real_model_repairs': 0,
                          'execution': asdict(execution), 'score': asdict(score),
                          'status': 'fixture_pass' if passed else 'fixture_fail'}, sort_keys=True, indent=2))
        return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
