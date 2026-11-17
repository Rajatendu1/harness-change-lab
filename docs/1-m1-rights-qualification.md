# M1 rights qualification

Reviewed on 17 November 2026. This is source-license research for the project, not legal advice. No terms were accepted and no benchmark data was downloaded.

## Current source signals

| Source | Current evidence | Intended harness use | Qualification result |
| --- | --- | --- | --- |
| Flask pinned source | BSD-3-Clause license file at the pinned base, SHA-256 `489a8e1108509ed98a37bb983e11e0f7e1d31f0bd8f99a79c8448e7ff37d07ea` | Clone, install and test the pinned public source in an isolated runner; do not vendor the source into this repository | Execution-only use has a clear license signal. Keep the license URL and hash in provenance. |
| Requests pinned source | Apache-2.0 license file at the pinned base, SHA-256 `c12dd61a3868c674312e979d0ec179ee84c82e8e63c742875238ac912fbd1bac` | Same as Flask | Execution-only use has a clear license signal. Keep the license URL and hash in provenance. |
| xarray pinned source | Apache-2.0 license file at the pinned base, SHA-256 `73ba74dfaa520b49a401b5d21459a8523a146f3b7518a833eea5efa85130bf68` | Same as Flask | Execution-only use has a clear license signal. Keep the license URL and hash in provenance. |
| Pylint pinned source | GPL-2.0 license file at the pinned base, SHA-256 `f97b14080de8b8490d60eb3d620ebc419943e0779466d1dd0d5d6f68fe195dcd` | Clone, install and test the pinned public source in an isolated runner; do not vendor the source into this repository | GPL permits use and modification, with copyleft obligations when GPL code or a derivative work is distributed. The current harness does not vendor Pylint, but accepting this task is a project policy decision because future distribution or bundling would need a GPL boundary. |
| pytest pinned source | MIT license file at the pinned base, SHA-256 `ca836a5f9ecca3b2f350230faa20a48fb8b145653b5568d784862df864706b9b` | Same as Flask | Execution-only use has a clear license signal. Keep the license URL and hash in provenance. |
| SWE-bench source code | MIT license in `SWE-bench/SWE-bench` | Reference the benchmark tooling and provenance | The MIT code license does not itself license the Hugging Face dataset content or metadata. |
| `princeton-nlp/SWE-bench_Lite` dataset | Current Hub API: public, not gated, SHA `6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2`, no license field, no license tag and no license in card data | Candidate selection/provenance only; no dataset rows, patches, problem statements or test patches used in M2 | Dataset terms remain undeclared. Public access is not a clear reuse or redistribution grant. |
| `SWE-bench/SWE-bench_Lite` dataset | Current Hub API: public, not gated, SHA `b0dde1093fe417d83b7184254edf8199c1f0dff5`, no license field, no license tag and no license in card data | Candidate selection/provenance only; no dataset rows, patches, problem statements or test patches used in M2 | Dataset terms remain undeclared. Public access is not a clear reuse or redistribution grant. |

## Observed source URLs

- Flask license: https://raw.githubusercontent.com/pallets/flask/d8c37f43724cd9fb0870f77877b7c4c7e38a19e0/LICENSE.rst
- Requests license: https://raw.githubusercontent.com/psf/requests/36453b95b13079296776d11b09cab2567ea3e703/LICENSE
- xarray license: https://raw.githubusercontent.com/pydata/xarray/a64cf2d5476e7bbda099b34c40b7be1880dbd39a/LICENSE
- Pylint license: https://raw.githubusercontent.com/pylint-dev/pylint/182cc539b8154c0710fcea7e522267e42eba8899/LICENSE
- pytest license: https://raw.githubusercontent.com/pytest-dev/pytest/6995257cf470d2143ad1683824962de4071c0eb7/LICENSE
- SWE-bench code license: https://github.com/SWE-bench/SWE-bench/blob/main/LICENSE
- Legacy dataset metadata API: https://huggingface.co/api/datasets/princeton-nlp/SWE-bench_Lite
- Current dataset metadata API: https://huggingface.co/api/datasets/SWE-bench/SWE-bench_Lite
- Official SWE-bench Lite page: https://www.swebench.com/lite

## What can be finished without the user

The project can finish the technical and source-license work without asking the user to perform review:

- Keep checking whether either Hugging Face dataset adds a license field or tag.
- Keep the pinned upstream license URLs and file hashes current.
- Preserve the current boundary: no Hugging Face rows, patches, problem statements or test patches; use original public GitHub issues, pull requests, repositories and test commands.
- Prepare an independent task-spec review packet and have a separate reviewer inspect it. This review does not need another external run because the M2 run page, workflow, manifests and execution evidence are already recorded.
- Prepare a source-only alternative that uses direct GitHub issue/PR provenance instead of SWE-bench Lite identifiers, if the project chooses to avoid the undeclared dataset-metadata risk.

## What needs the user's decision

These are legal or policy choices, not technical review tasks to hand back to the user:

1. Whether to keep the GPL-2.0 Pylint task under a distribution boundary that does not vendor or bundle Pylint code in the harness repository.
2. Whether to accept or remove SWE-bench Lite-derived provenance while the dataset license remains undeclared.
3. Whether to ask SWE-bench maintainers for a dataset-license clarification. Sending that request would be a new external communication and needs its own approval.
4. Whether any future coding-agent, model or benchmark-data run is allowed. That remains outside the current authority.

## Proposed next substantive scope

Prepare a source-only M1 manifest proposal for review. It would keep the same five upstream repair cases and M2 evidence, replace SWE-bench-specific dataset fields with direct GitHub issue/PR provenance, and leave all tasks as candidates until independent review and the Pylint GPL policy decision are complete. This proposal should be reviewed before replacing the current registry, because it changes suite provenance and must not silently redefine acceptance.
