# Corrected Click model-free runtime check

18 November 2026. The corrected package passed its first and only [manual run](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44316075709). The [job](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44316075709/job/134842409467) took 72 seconds and completed at 13:41:37 UTC.

## What actually ran

The runner verified the reviewed archive and its 64-file content manifest, assembled 130 hash-checked build inputs (136,393,186 bytes), built separate editing and verifier images, then exercised the public Click task with fresh scoring containers.

| Control | Focused tests | Outcome |
| --- | --- | --- |
| Unchanged base | 3 failed, no skips | Expected negative control |
| Known upstream fix | 3 passed, no skips | Expected positive control |
| Actual Aider process with a fixed canned response | 3 passed, no skips | Scripted edit collected and separately scored |

The result records tokenizer-container cleanup and built-image cleanup as confirmed. There were no uploaded Actions artifacts, API keys or repository secrets in this workflow.

## What this does not mean

There were zero real provider calls and zero model repairs. The nested `provider_attempts: 1` record describes the local canned transport, not a request to Groq or another inference service. Its usage is unknown because it is a fixture, not billed model inference.

This confirms the corrected package's narrow model-free Click editing/scoring path in the hosted runtime. It does not test live provider transport, general coding-agent effectiveness, a multi-task paired comparison, adversarial scoring integrity or full harness completion. The generic `runtime_qualified` fields remain false; do not reinterpret this run as blanket runtime certification. Reference tests are publicly bundled, not hidden from future agents.

The earlier diagnostic dispatch stopped during setup. Local reproduction found stale helper-wheel manifest hashes after the diagnostic source change. This package regenerated both helper manifests and passed actual local public-artifact hydration and exact context checks before this separate run. The earlier failure is not a model failure and was not silently retried.

## Reproducibility

- Runtime archive SHA256: `8dbe91adb61072b7e6e772a2cf4423d4a632900fc7f3f316c93761353ab0164a`.
- Workflow head: `598b56361ecf29e5c696202a83dd1713c847f147`.
- One dispatch, attempt 1, standard Ubuntu runner, ten-minute job cap, no retry or paid fallback.
- No permission for another job or any model request follows from this result.
