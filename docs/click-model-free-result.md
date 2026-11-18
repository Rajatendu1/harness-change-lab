# Click task mapping: model-free result

18 November 2026. The [single diagnostic run](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44235253963) passed. The [job and logs](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44235253963/job/134569718316) took 1m15s; the input/build/diagnostic step took 1m3s.

This was a real public Click task with a known canned response. It made **zero model-provider calls** and demonstrates **zero AI repairs**. It is separate from the earlier fictional fixed-scope runtime qualification.

## What ran

- Exact public Click parent revision `8abb77a8432e03ed14a95f972b44f905279415a7`, with only `src/click/formatting.py` editable.
- Hash-checked public dependencies, tokenizer data and source inputs. Separate agent and verifier images were built with offline dependency installation.
- The unchanged source failed all three focused regression cases. The known upstream fix passed all three. Neither control counts as an agent repair.
- Actual containerized Aider received a small canned SEARCH/REPLACE response through the bounded gateway. Exactly one gateway attempt returned. Its collected source then passed all three focused cases in a fresh verifier container, with no skips.
- The tokenizer container was removed and built images were removed. Candidate collection and scoring completed through the cleanup-gated controller path.

The final record is `click_model_free_task_mapping_passed`, with `real_provider_calls: 0`, `real_model_repairs: 0` and `adversarial_integrity_verified: false`. The input summary's `prepared_exact_input_context_not_built` value describes the pre-build context validation, not the final run outcome. It is an awkward internal label, not a claim that the completed workflow skipped the build.

## Reproducibility

- [Workflow revision](https://github.com/Rajatendu1/harness-change-lab/commit/21fa1fe9e8d036cf22d26cc9f6125173dadd8548).
- [Reviewed runtime-only archive](https://github.com/Rajatendu1/harness-change-lab/blob/main/1-harness-click-model-free-runtime.tar.gz), SHA-256 `1e3fb8ccc992456cb815c1d349a5c2005e9fb800e0d97f4a48aa3f525c0e249a`.
- 64 archive files: 63 runtime/source/input files and their manifest. No private chats, credentials, development logs or stored build artifacts.
- The archive downloaded from GitHub matched the reviewed bytes before dispatch. The workflow was dispatched once, with no retry, on the standard Ubuntu runner and a ten-minute job limit.
- Local development tests before dispatch: 283 passed, no skips. These are local checks, not 283 live container trials. The earlier 92-file readable-source publication and its 244-test result are an older snapshot; this new Click implementation is in the reviewed runtime archive.

## What this does not prove

The response supplied the known edit. No model chose or discovered a repair. This is one narrow regression mapping, not broad Click compatibility, comparative harness quality, a performance benchmark or a production-ready service. Scoring trusts the verifier process; adversarial scoring integrity remains unproven. Provider usage is unknown for the canned response because there was no provider.

## Next gate

A live model attempt remains unexecuted. It needs separate, current permission for a fresh temporary credential and one bounded free-tier request. Earlier model-run grants are closed and are not reused here. Any attempt must retain public-input-only scope, no retries, no spending or upgrade, separate scoring, and confirmed credential/secret cleanup even when the run fails.
