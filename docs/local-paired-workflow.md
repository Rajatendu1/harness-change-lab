# Local paired-fixture workflow and release checks

The current development source can run the existing local canned fixture and verify/render its journal without calling a real provider. This is software plumbing, not an AI repair benchmark.

From the repository root, using an already provisioned local agent/verifier runtime:

```sh
python -m scripts.paired_workflow fixture --runtime-root /path/to/runtime --output-directory /new/journal
python -m scripts.paired_workflow review /new/journal
```

No installation fallback or live-model mode exists. The fixture command writes a plan first, uses one local canned request budget per trial, records each result and finalizes via the paired controller. Two synthetic tasks include a repair and deliberate test-setup failure. Two configurations receive different fixed responses. Review invokes no child/provider, verifies the plan and record hashes, recomputes the comparison and requires exact agreement with the saved report. Hashes establish consistency, not honest producers or authenticated execution.

Exit codes: 0 no detected regression, 1 regression, 2 invalid/incomplete, 3 insufficient evidence. Fixture evidence always abstains. The report retains excluded setup errors, unknown time/usage and per-trial observations. Editing-child time is not total workflow latency. Canned token values are invented fixture plumbing. Cost is not computed without verified price/billing evidence.

## Observed local control

Four actual local Aider canned-edit trials completed using the existing runtime: one synthetic repair pair was included (baseline failed, candidate passed); the deliberate setup-error pair was excluded. Verdict insufficient_evidence. Each editing child took about 3.1 seconds. A repeated review reproduced byte-identical text without another child or provider call. This is local namespace-runtime evidence, not Docker qualification or a real repair. A fresh-checkout import failure found before those observations was fixed by module-based child launch from repository root; the failed partial journal was not treated as complete.

Ten reporting tests cover tampering, partial journals, excluded outcomes, unknown observations, fixture labels, unsafe identifiers, output-directory reuse and review without child execution. The integrated development suite reports 387 tests OK with no skips in the development environment; independent review reported 387 OK with 19 environment-gated skips. These are distinct environments, not a single combined run.

## Release consistency

```sh
python scripts/check_runtime_package.py 1-click-coherent-runtime-r2.tar.gz \
  --sha256 8dbe91adb61072b7e6e772a2cf4423d4a632900fc7f3f316c93761353ab0164a \
  --workflow .github/workflows/manual-click-model-free.yml --working-tree .
```

This offline check verifies the selected archive's full member/hash manifest and deterministic actual helper builds. Working-tree helper metadata is checked separately. Main's stale helper metadata was corrected by regeneration after excluding unnecessary Flask task/planning modules from the Click agent wheel. Verifier helpers retain those modules. This is scope minimization; no protected-reference leak was found in Flask task metadata. Future Flask editing dependencies need separate design and review.

The workflow check is an exact allowlist of the reviewed manual/no-key template, varying only the selected archive filename and SHA. Any legitimate workflow edit needs template review and a new template hash. This is deliberately narrow, not a general YAML security parser. A pass means package coherence, not runtime qualification or execution authority. The exact immutable r2 archive and prior runtime result remain unchanged. Future selected release records should identify source base commit, dirty diff hash, archive hash and workflow hash separately; the old r2 source commit is not inferred from its workflow head.

## Remaining limits

Older Click run44236654519 failed provider transport with cause/usage unresolved. Later run44297299419 failed setup because of stale helper manifests established by local reproduction before provider construction. Corrected no-key run44316075709 passed. Neither failure is a model loss; the canned pass is not a model repair.

Actual task editing beyond Click, rights-cleared multi-task paired collection, known provider transport/usage, sample calibration and adversarial scoring remain open. The separate Flask runtime evidence is narrow reference scoring only. No changed-image runtime qualification, full harness completion or production-readiness claim follows from this maintenance.
