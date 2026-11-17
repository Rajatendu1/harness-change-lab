# M7 direct-upstream verifier run

Run date: 17 November 2026.

The owner-authorized M7 verification batch was dispatched once as GitHub Actions run [#1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408). The run completed successfully in 1 minute 32 seconds, including one manifest-preparation job and 15 task/trial jobs. This was the single approved batch; no job was retried.

## Run identity

- Repository commit: `ddb84e2cf6fd9cb405861413eb47331721b93ea9`
- Workflow: `.github/workflows/m7-direct-upstream-verifier.yml`
- Workflow SHA-256: `704f4241652136846d921571596f54cc54afa4fe8e9e3dbfcfe9d8bd56df324d`
- Manifest: `proposals/m7-direct-upstream-verifier.manifest.json`
- Manifest contract identity SHA-256: `ede5692cac16280eeec703d62d1fed419ebb2c93c0220f221c3ce58349df4bc9`
- Manifest raw-file SHA-256: `7a64bce399618dcab92aef09768bc2f1d5a14efca6db503c5fc76df13fc0ea45`
- Result records: `proposals/m7-direct-upstream-verifier.results.jsonl`
- Result-file SHA-256: `57ee20928a41846097e163837500b4e021ce50b9be145bc0915189e2738162b2`
- Validation summary: `proposals/m7-direct-upstream-verifier.validation.json`
- Validation-file SHA-256: `54e03bd666c0f75f21af20fa0b425f3e5088282ab60367f9f1a85606716d6c73`
- Trigger: one explicit `workflow_dispatch`
- Runner label: `ubuntu-22.04`
- Trial plan: five tasks, three trials each, 15 total
- Job timeout: 20 minutes per task/trial
- Maximum concurrent task/trial jobs: 5
- Benchmark data: not downloaded or used
- Secrets, model credentials and artifact uploads: none
- Automatic retry: none

## Result contract validation

All 15 supplied `m6-run-result-v0` records match the prepared manifest. The base verifier ended as an ordinary pytest failure and the fixed verifier passed in every trial. The validation command reported `results_contract_valid`, five tasks, 15 trials, zero model or agent runs, zero benchmark-data use, zero artifact uploads and zero automatic retries.

```sh
python -m harnesslab.cli validate-run-results \
  proposals/m7-direct-upstream-verifier.manifest.json \
  proposals/m7-direct-upstream-verifier.results.jsonl
```

The normalized result-set digest is `1791f96e8981f9b1bbae3e9a7926606da28274950d33c1ae0d86c439a90d2020`.

## Results

| Task | Trials | Base failures | Fixed passes | Jobs |
| --- | ---: | ---: | ---: | --- |
| `m1-click-hyphenated-help-wrap` | 3 | 9 | 9 | [1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136475), [2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136171), [3](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136269) |
| `m1-flask-dotted-blueprint` | 3 | 6 | 6 | [1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136110), [2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136228), [3](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136196) |
| `m1-pytest-number-docstring` | 3 | 3 | 3 | [1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136273), [2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136384), [3](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136340) |
| `m1-requests-decode-unicode` | 3 | 3 | 3 | [1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136157), [2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136280), [3](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136308) |
| `m1-xarray-unstack-single-dim` | 3 | 3 | 3 | [1](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136162), [2](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136159), [3](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44089045408/job/134059136183) |

Every task/trial job completed successfully. Each job recloned its pinned public upstream repository, applied only the fixed commit's focused test patch to the direct-parent base, observed the expected base failure, reset to the fixed commit and observed the focused verifier pass.

## Provenance and boundary

The result JSON records were extracted from the run's GitHub job summaries and validated locally against the recomputed manifest. The M6 validator checks record identity, completeness and policy fields; it does not execute, replay or authenticate GitHub Actions logs. GitHub reports run attempt 1 with 16 successful jobs.

This run verifies harness execution and result intake for the accepted direct-upstream suite. It is not a coding-agent result, model-quality result, benchmark-dataset run, production gate or proof that the harness is finished. Further batches, retries, AI evaluation, benchmark-data use and paid services require separate authority.

## Acceptance status after this run

The five-task suite remains `upstream_source_verified_accepted`: five tasks accepted, five with upstream-source execution evidence, five with recorded read-only engineering review, zero rights reviews pending and zero model or agent runs. Remaining acceptance work is separate authority before any coding-agent, model or benchmark-data run.
