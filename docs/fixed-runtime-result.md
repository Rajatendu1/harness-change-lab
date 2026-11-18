# Fixed model-free Docker qualification

Snapshot: 18 November 2026. This is a fixed synthetic adapter check, not a real AI coding benchmark or a production-readiness claim.

## Result

[Run 44226880573](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44226880573) passed in 1 minute 42 seconds on a standard Ubuntu 24.04 GitHub-hosted runner. The workflow revision is `777015b2a01d1336170c3b076efebbea16f0ab31`.

The runtime-only source package SHA256 is `70d67bb6c8a6a5f78180b32a813e5b8bdd2bf2b3b588c5a9500bced458975036`. It contains exact runtime source and fixed dependency metadata, without repository history, private documents, previous logs or credentials. It is not a complete readable source-tree publication.

Observed runtime identity: Python 3.10.22, Git 2.39.5, Aider 0.86.2. The build context was checked against an exact hash allowlist: 128 files, 132,744,511 bytes. Two separate local images were built with offline hash-required binary dependencies.

## Checks that passed

- Fresh-container identity and process-limit checks. Controller-observed PID-limit event increase: 2.
- Deliberate bounded memory-pressure check. Controller-observed OOM-kill event increase: 3. The same sole keeper remained running.
- CPU throttling check. Controller-observed throttling event increase: 30.
- Workspace and temporary-storage capacity checks, and a forced wall-time timeout.
- Separate verifier controls: unchanged and wrong fixtures failed; the known-correct fixture passed. No tests were skipped.
- One canned-response Aider edit matched the expected fixture change and passed a separate protected fixture score.
- Tested containers were removed and their absence checked. Built-image cleanup was confirmed.

The fixed editing lifecycle also runs dummy-private-file, network, Docker-socket and gateway-socket denial checks before importing the fixture. These are bounded checks of the declared fixture policy, not universal isolation proof.

## Failure history and correction

[First attempt](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44222436805) failed at the memory stage and stopped before later checks. [Diagnostic attempt](https://github.com/Rajatendu1/harness-change-lab/actions/runs/44224797340) showed that the deliberately induced OOM event set Docker's OOM flag while the original keeper remained running. A generic no-OOM keeper check rejected that expected condition.

The correction is specific to the deliberate memory-pressure probe. It requires an independently increased OOM-kill counter, exact resource limits, the unchanged live keeper, and no extra processes. Generic candidate, PID and CPU observation checks still reject an OOM flag. No resource limit or allocation cap was relaxed. The changed local source passed 244 development tests before the final hosted check.

## Limits

- Zero real provider calls and zero demonstrated real AI repairs in these three runs. A canned response is not model reasoning.
- Protected scoring is a trusted-process boundary, not adversarial scoring integrity.
- Nested reusable fixture reports retain conservative `runtime_qualified: false`, `qualification_complete: false` and older prepared/local/injected evidence labels. The top-level result is `fixed_adapter_scope_passed`, supported by the actual Docker workflow and fixed entry point. It does not override those scope limits.
- No saved artifacts, cache upload, model credentials, paid runner or automatic retry was used. Historical failed runs remain failed.
- A later real-model trial needs its own fixed transport, source scope, request budget, score controls and permission. This result grants none of those.
