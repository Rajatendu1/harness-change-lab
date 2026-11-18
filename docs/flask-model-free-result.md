# Flask model-free runtime result

18 November 2026: the separate Flask reference-verifier qualification passed on its first and only dispatch.

- [Run](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44258824645), attempt1, completed successfully in35seconds.
- [Job and logs](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44258824645/job/134646921095).
- Workflow revision: `d9ef29c8effa897ab11f3ecb861614763fc65e97`.
- Runtime archive SHA256: `a4fb27c9a99dd126e6dd0f4e2800f201d7df274a7e2ba7c2ffd2cdfff4c2e1d8`.
- Runtime package: `1-flask-model-free-runtime-review.tar.gz`, 110 hash-checked input/helper files. The upload interface added the filename's `1-` prefix; workflow path was matched to that observed filename without changing archive bytes.

## What executed

One manual standard public Ubuntu24.04 job, under its ten-minute cap, built a separate offline-installed Flask verifier image from an immutable Python base. The fixed driver checked actual Python3.10.22, image/config identities, isolation denials, keeper-only process state and PID/CPU/memory controls. It used no Aider, model, provider credential or real provider request.

Three fresh verifier containers ran the same narrow blueprint-name reference test:

| Source | Collected | Failures | Skips | Expected outcome |
| --- | ---: | ---: | ---: | --- |
| Unchanged pinned base | 1 | 1 | 0 | Reference failure |
| Known upstream fix | 1 | 0 | 0 | Reference pass |
| Name-only reference patch | 1 | 0 | 0 | Reference pass |

The intended protected-directory classname mapping was exercised, not the earlier flat-path local rehearsal. The task's source selection, historical benchmark-selection caveat and narrow scope are explained in [preparation](flask-preparation.md).

## Cleanup evidence

The qualification result reported probe-container removal confirmed and both newly created images removed with absence checks. Its separate always-cleanup step then checked four recorded container names and two recorded image IDs and returned `flask_recorded_identity_cleanup_confirmed`. Each reference scorer also required confirmed container removal before accepting its score.

The workflow requested no cache export, stored Actions build artifact or registry push. No automatic retry occurred. Standard platform checkout authentication is distinct from model credentials; checkout used read-only contents access and removed its temporary authentication. Build intermediates were not exported and existed only on the ephemeral hosted runner. The run does not claim to audit GitHub's underlying infrastructure.

## What this does not prove

This is real-source, model-free runtime/reference evidence. It is not an AI repair, an agent editing result, a before/after harness comparison, a whole-Flask test run or a production-readiness verdict. The single test has weak semantic coverage. The public reference tests must not be represented as hidden from a future agent. Pytest results remain trusted-process evidence, not proof against a malicious candidate forging reports. Individual scorer rows deliberately retain `runtime_qualified:false` and `adversarial_integrity_verified:false` rather than imply general safety.

There were zero agent/model/provider runs and zero model repairs. Existing Click run inputs and evidence were not changed. This one-job approval is consumed; no retry or model request follows from it. Broader runtime/task coverage and genuine planned paired model evidence remain outstanding. The harness project is not complete; the NLP project follows it.
