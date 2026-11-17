# Proposed manual CI pilot, pending owner approval

This is a review document, NOT an installed workflow. The proposed first run is
an isolation and resource check with fixed test code. It cannot satisfy the
real-agent or five-repair-task milestone.

Proposed public repository: `Rajatendu1/harness-change-lab`.

- Existing signed-in account; no new account, OAuth grant, PAT or gh CLI access.
- Standard `ubuntu-24.04` only, at most 10 minutes per explicit manual run.
- `contents: read` only. No model, issues, pull-request or repository write scope.
- Checkout credentials are not persisted. No secrets passed to the test process.
- No Actions artifact upload or cache. No image/package publication or registry
  push. No larger/self-hosted runner. No paid inference or billing change.
- The pinned Python image is pulled anonymously. No Docker registry login.
- Refuse missing Docker, less than 8 GiB free disk or image size above 512 MiB.
- Container has no network, host bind mount, device, Docker socket or privilege;
  runs as UID65534 with a read-only root, no capabilities/new privileges,
  256MiB RAM,1CPU,64PIDs and a temporary /tmp; fixed process timeout15seconds.
- The controller verifies the actual Docker inspect values and exit state, then
  removes the container. Logs contain fixed probe results, not credentials.
- Only after this passes should task-suite and real-agent sandbox acceptance be
  attempted. A container is not a hardened multi-tenant security service.

Proposed YAML for later review and installation:

```yaml
name: Manual container feasibility
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  isolation-smoke:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09
        with:
          persist-credentials: false
      - name: Fixed-code isolation smoke only
        run: python3 scripts/container_smoke.py
```

The checkout SHA was resolved from the official actions/checkout v5 tag on
17 Nov2026. The image manifest was read from the Docker Hub official Python
repository the same day. Recheck supply-chain provenance before actual execution.
No model response or target repository is executed by this pilot.

Official sources:
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
- https://hub.docker.com/_/python
