# Supplied runner evidence intake

The `compare-click-evidence` command connects versioned Click runner summaries to paired comparison without executing an agent or provider request.

```sh
python -m harnesslab.cli compare-click-evidence plan.json evidence.json
```

Exit codes: `0` no detected regression, `1` regression, `2` malformed/inconsistent input, `3` insufficient evidence. The current adapter supports one pinned Click task only, so it cannot clear the comparison's minimum-two-task policy. This is an evidence-handling path, not a new benchmark result.

## Boundaries

- Hashes detect inconsistent inputs. They do not authenticate execution, establish approval, or prove that a producer told the truth.
- Job URLs are supplied references. The command validates their shape and refuses reference reuse, but makes no network request and does not verify their contents.
- Task revision, verifier identity, configuration identities, baseline/candidate order, trial count and statistical policy are fixed by the supplied plan. The command rejects incomplete slots, duplicates, changed digests and unknown envelope fields.
- A canned response on a real public task is excluded from model-repair metrics. Reference controls cannot become repairs. Missing cleanup, failed transport and unverified scoring are exclusions, not failed model tests.
- Scored evidence requires the expected three-case base/fixed controls, one returned request, completed focused scoring and runtime cleanup. This remains a consistency check on supplied trusted-process claims, not adversarial proof.
- Any excluded pair prevents a comparison verdict. Fixture evidence always abstains. One task cannot establish broad harness performance, even if the caller labels it live.
- Provider usage may remain unknown. Intake never substitutes zero for unknown usage and never makes another request to investigate.
- External key revocation and secret removal are a separate operational responsibility. Runtime image/container cleanup does not prove credential cleanup.

## Plan schema

The exact top-level keys are `schema`, `tasks`, `configurations`, `configuration_order`, `trials`, `fixture_only` and `policy`.

- `schema`: `click-paired-intake-plan-v1`.
- `tasks`: the exact task ID `m1-click-hyphenated-help-wrap`, mapped to `revision` and `verifier_sha256` from `harnesslab.click_task` and `harnesslab.click_verifier_child`.
- `configurations`: exactly two distinct safe names mapped to distinct lowercase SHA-256 identities.
- `configuration_order`: the two names in baseline, candidate order.
- `trials`: integer 1 through 20, indexed from zero in evidence rows.
- `fixture_only`: strict boolean. Use true for synthetic rehearsals. Setting false does not authenticate evidence.
- `policy`: exactly `min_tasks`, `margin`, `confidence`, `resamples` and `seed`, checked by the comparison engine before intake, even if all records are excluded.

SHA-256 digests use UTF-8 JSON with sorted keys, compact separators and no non-finite numbers. `harnesslab.evidence_intake.digest` is the implementation. Duplicate JSON keys and non-finite JSON constants are refused.

## Evidence schema

`evidence.json` is an array with every planned configuration/task/trial slot exactly once. Each exact envelope has:

- `schema`: `click-runner-evidence-v1`.
- `plan_sha256`: digest of the supplied plan.
- `configuration`, `task_id`, `trial`: a planned slot.
- `execution_ref`: the observed GitHub Actions job URL, not a guessed link. A job reference can fill only one slot.
- `result_sha256`: digest of `result`.
- `result`: the parsed controller summary, retaining its evidence class rather than relabeling it.

This adapter accepts the known live Click result class only for scored model outcomes. It separately recognizes and excludes the canned real-task class and reference classes. Unknown future result formats fail closed until an adapter is reviewed.

The output retains only hashes, planned identities, supplied job references, allowlisted classification reasons and the comparison. It does not copy arbitrary runner fields, raw request/response content or exception messages into the report. CLI errors do not echo input bodies or paths. Inputs are bounded to 1 MiB for the plan and 8 MiB for evidence.

## Validation on the observed records

The actual model-free diagnostic is classified as canned, not a model repair. The single live attempt is classified as a transport exclusion, not a failed model test. They are different evidence classes and were not a planned baseline/candidate experiment, so no comparative result was manufactured from them.

- [Model-free record](click-model-free-result.md)
- [Single live-attempt record](click-live-attempt-result.md)

Local synthetic tests exercise positive intake, abstention and malformed evidence paths. They do not create new model-quality evidence or qualify a changed container image. Later source changes require regenerated helper manifests and image checks before any future execution.

The broader project remains a reliable before/after harness comparison workflow. The NLP project follows it; this intake work is part of the harness, not a substitute NLP milestone.
