# One live Click attempt: excluded, no repair

18 November 2026. The [single approved live run](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44236654519) ended with a failed provider transport attempt. It was not retried. The [job and logs](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44236654519/job/134574311448) took 1m24s.

## Observed result

- Both public reference controls behaved correctly: unchanged Click source failed all three focused cases; the known upstream fix passed all three, with no skips.
- The lifetime request budget recorded exactly one attempted provider transport, with outcome `failed` and usage unknown.
- No model response or repair was collected for scoring. The outcome is excluded at `request_audit`, with `score_status: not_run_collection_excluded` and zero demonstrated model repairs.
- The tokenizer container and built images were cleaned up.
- After the terminal run, the dedicated Groq key was revoked and its absence verified in the live key list. The temporary repository Actions secret was deleted and the repository's empty secret list verified. An existing unrelated key was left unchanged. External credential cleanup happened after the job; the job's own false cleanup fields correctly do not claim those later actions.

## What is unknown

The transport deliberately suppressed exception and response-body details. That protected secrets but did not retain enough non-sensitive diagnostic metadata. This run therefore does not establish whether the failure was an HTTP rejection, network/TLS problem, timeout or another transport error. Do not label it a quota failure or a model-quality failure.

One transport attempt is not proof that the provider completed inference, and unknown usage is not zero usage. A current provider log view showed only older records, so it did not settle this attempt's cause. No further provider request was made to investigate.

## Scope and reproducibility

The attempt used the same bounded public Click task mapping as the [successful model-free diagnostic](click-model-free-result.md), not the earlier fictional fixture. Only public code/task instructions were eligible for the provider request. There was no paid runner, spending, upgrade, fallback model or raw prompt/response publication.

- [Workflow revision](https://github.com/Rajatendu1/harness-change-lab/commit/97856965cb6f1a769b2f73ab94e95120613a7536).
- Reviewed live runtime archive SHA-256: `0b80bf5e071660abb071b269e7fd4cee47c3c99d7307db121f26f40f4303e5d1`.
- Archive and workflow live bytes were checked before the one dispatch.
- Local development preparation: 293 passing tests, no skips. These are not 293 live trials.
- Trusted-process scoring only. Adversarial integrity and general repair quality remain unproven.

## Next engineering work

Improve safe transport diagnostics locally: retain a small allowlisted failure category and numeric HTTP status without credentials, endpoint contents, response bodies, raw chats or automatic retries. Test rejection, timeout and cleanup paths with fake transports before considering another live attempt. This run's authority is consumed; no new credential or provider attempt is implied by fixing the code.
