# Flask narrow-task preparation

This is a second real-code verifier preparation step for the harness project. It is not a model repair result and is not a before/after harness comparison. The NLP project remains after the harness project.

## Task boundary

The prepared task asks for blueprint names containing a dot to raise `ValueError`, with edits limited to `src/flask/blueprints.py`.

Sources:

- Issue: https://github.com/pallets/flask/issues/4041
- Pull request: https://github.com/pallets/flask/pull/4045
- Fix: https://github.com/pallets/flask/commit/08e459e823235eecd86c635653f4bd6d6003c2b3
- Base: `d8c37f43724cd9fb0870f77877b7c4c7e38a19e0`

The historical corpus card also named an endpoint/view-function test. The fix changes exception behavior for those conditions as well. This preparation excludes that broader test rather than silently broadening a blueprint-name issue. It has a distinct task ID, `prepared-flask-blueprint-dotted-name`, and does not rewrite or replace the earlier suite.

The original candidate selection was SWE-bench Lite-derived. Current source bytes were fetched directly from pinned upstream sources, without retrieving benchmark rows. That does not make the original selection independent of the benchmark.

## Local evidence

The one directly relevant upstream test is `test_dotted_name_not_allowed`. Its original function body and parameters are retained. The small protected file adds two None-returning fixtures because its app/client parameters are unused. No full Flask conftest is imported. Protected SHA256: `8e44d33f91f5a8166bedcc61f179f75cb144055e356f0d97999a4a8730ae161a`.

| Input | Local result |
| --- | --- |
| Pinned unchanged base | 1 collected, 1 failed |
| Known upstream fix | 1 collected, 1 passed |
| Name-only reference patch | 1 collected, 1 passed |

Each control used a fresh source copy, a read-only source mount, a network namespace, no automatic pytest plugins and bounded time/memory/output. These are trusted-process local controls. They do not prove Docker execution, adversarial scorer integrity, an AI repair, broad Flask compatibility or model quality. A malicious candidate can forge its own pytest report. No provider request, credential, spend or external runner was used for these controls.

Twelve wheel artifacts were downloaded without source builds. Their filenames, sizes and SHA256 hashes were checked against PyPI's version metadata. Installation into a dedicated local environment used only the downloaded wheelhouse. The compatibility environment uses Werkzeug2.0.0, Jinja2 3.0.0, MarkupSafe2.0.1, itsdangerous2.0.0, click8.0.0 and pytest8.3.5 plus pinned test dependencies. These are historical reproduction pins, not a current production recommendation or a security audit. Wheel license-file hashes and available license metadata are recorded separately.

## New preparation contracts

- `flask_task.py` binds the exact 25 base filenames and SHA256 hashes. The base validator rejects changes, additions and missing files.
- `flask_preparation.py` accepts only the exact base plus one hash-bound protected test. Only the declared source file may change. Existing bounded archive parsing rejects unexpected paths and members.
- Its local report parser requires the exact test name/class, one suite and case, no collection errors or skips, and matching exit/failure counts. It rejects declarations, oversized XML and abnormal exits. It does not authenticate reports or make the scorer safe against hostile code.
- The preparation scorer contract is excluded from the editing helper package and included in the verifier helper package. No new helper image has been built or qualified.

## Still required

A separate Flask-only verifier recipe and exact 16-file dependency/helper context are prepared, not built. The context records its exact byte total, contains neither Flask source nor its protected test, refuses unlisted files and uses only hash-pinned binary wheels with network disabled for build steps. This validates a proposed input boundary, not an image or runtime. The base digest comes from previously recorded immutable candidate metadata, not a fresh availability check. Local controls used Python3.10.12; the candidate base advertises3.10.22, so fresh image controls are still required.

Do not alter the already executed Click image or immutable run archives to add Flask dependencies. Next qualify the separate source transfer and runtime controls in the intended external runtime, arrange any separately required run authority and only then consider model-free editing or a new paired experiment. No further provider call is authorized by this document.

One narrow task has weak semantic coverage. Passing it cannot support a general reliability claim. Genuine comparison requires a declared multi-task plan, complete matched trials and the existing evidence-intake exclusions. A canned edit, known fix or failed transport is never substituted for a live AI repair.
