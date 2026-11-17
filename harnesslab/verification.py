"""Prepared M1 verification plans, with no task or upstream-code execution."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .tasks import ManifestError, TaskSpec, suite_summary

_SHA = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_EVIDENCE_STATUS = "metadata-verified"
_EXECUTION_STATUS = "upstream-source-verified"
_RUN_URL = re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/actions/runs/\d+$")


@dataclass(frozen=True)
class SourceEvidence:
    id: str
    repo: str
    base_commit: str
    fixed_commit: str
    fixed_first_parent: str
    base_relation: str
    ancestor_gap_commits: int
    fixed_commit_kind: str
    issue_url: str
    issue_title: str
    pr_url: str
    pr_title: str
    test_files: tuple[str, ...]
    implementation_files: tuple[str, ...]
    test_patch_url: str
    test_patch_scope: str
    evidence_qualification: str
    license_spdx: str
    license_url: str
    license_file_sha256: str
    license_notes: str
    benchmark_dataset: str
    benchmark_url: str
    benchmark_sha: str
    benchmark_license_status: str
    status: str


@dataclass(frozen=True)
class ExecutionEvidence:
    id: str
    status: str
    run_url: str
    workflow_commit: str
    workflow_sha256: str
    runner_label: str
    job_timeout_minutes: int
    benchmark_data_used: bool
    secrets_model_credentials_cache_artifacts: bool
    artifacts_count: int
    summary_caveat: str
    python_version: str
    package_name: str
    package_version: str
    pytest_version: str
    base_exit_code: int
    base_duration_s: int
    base_failed_count: int
    fixed_exit_code: int
    fixed_duration_s: int
    fixed_passed_count: int
    base_commit: str
    fixed_commit: str
    test_patch_identity: str
    test_patch_source_url: str
    test_patch_applied_files: tuple[str, ...]
    test_patch_scope: str


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(mapping: dict[str, Any], key: str, *, min_length: int = 1) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or len(value.strip()) < min_length:
        raise ManifestError(f"evidence {key} must be a string of at least {min_length} characters")
    return value.strip()


def _sha(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping, key, min_length=40)
    if not _SHA.match(value):
        raise ManifestError(f"evidence {key} must be a lowercase 40-character commit SHA")
    return value


def _hex64(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping, key, min_length=64)
    if not _HEX64.match(value):
        raise ManifestError(f"evidence {key} must be a lowercase 64-character SHA-256 hex digest")
    return value


def _https(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping, key, min_length=12)
    if not value.startswith("https://"):
        raise ManifestError(f"evidence {key} must be an HTTPS URL")
    return value


def _bool(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ManifestError(f"evidence {key} must be a boolean")
    return value


def _int(mapping: dict[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ManifestError(f"evidence {key} must be an integer from {minimum} to {maximum}")
    return value


def parse_evidence(mapping: dict[str, Any]) -> SourceEvidence:
    """Validate one source-evidence record without trusting it as authority."""
    if not isinstance(mapping, dict):
        raise ManifestError("each evidence line must be a JSON object")
    source = mapping.get("source")
    license_info = mapping.get("license")
    benchmark = mapping.get("benchmark")
    if not isinstance(source, dict) or not isinstance(license_info, dict) or not isinstance(benchmark, dict):
        raise ManifestError("evidence needs source, license and benchmark objects")
    files = source.get("test_files")
    if not isinstance(files, list) or not files or not all(isinstance(item, str) and item for item in files):
        raise ManifestError("source.test_files must be a non-empty list of paths")
    implementation_files = source.get("implementation_files")
    if not isinstance(implementation_files, list) or not implementation_files or not all(isinstance(item, str) and item for item in implementation_files):
        raise ManifestError("source.implementation_files must be a non-empty list of paths")
    base_relation = _text(source, "base_relation")
    if base_relation not in {"direct-parent", "ancestor"}:
        raise ManifestError("source.base_relation must be direct-parent or ancestor")
    fixed_commit_kind = _text(source, "fixed_commit_kind")
    if fixed_commit_kind not in {"merge", "single-parent"}:
        raise ManifestError("source.fixed_commit_kind must be merge or single-parent")
    base_commit = _sha(source, "base_commit")
    fixed_first_parent = _sha(source, "fixed_first_parent")
    ancestor_gap_commits = _int(source, "ancestor_gap_commits", minimum=0, maximum=100000)
    if base_relation == "direct-parent" and (fixed_first_parent != base_commit or ancestor_gap_commits != 0):
        raise ManifestError("direct-parent evidence needs fixed_first_parent equal to base_commit and zero ancestor gap")
    if base_relation == "ancestor" and (fixed_first_parent == base_commit or ancestor_gap_commits < 1):
        raise ManifestError("ancestor evidence needs a different fixed_first_parent and a positive ancestor gap")
    status = _text(mapping, "status")
    if status != _EVIDENCE_STATUS:
        raise ManifestError(f"evidence status must be {_EVIDENCE_STATUS}")
    return SourceEvidence(
        id=_text(mapping, "id", min_length=3),
        repo=_text(source, "repo", min_length=3),
        base_commit=base_commit,
        fixed_commit=_sha(source, "fixed_commit"),
        fixed_first_parent=fixed_first_parent,
        base_relation=base_relation,
        ancestor_gap_commits=ancestor_gap_commits,
        fixed_commit_kind=fixed_commit_kind,
        issue_url=_https(source, "issue_url"),
        issue_title=_text(source, "issue_title", min_length=10),
        pr_url=_https(source, "pr_url"),
        pr_title=_text(source, "pr_title", min_length=10),
        test_files=tuple(item.strip() for item in files),
        implementation_files=tuple(item.strip() for item in implementation_files),
        test_patch_url=_https(source, "test_patch_url"),
        test_patch_scope=_text(source, "test_patch_scope", min_length=10),
        evidence_qualification=_text(source, "evidence_qualification", min_length=10),
        license_spdx=_text(license_info, "spdx_id", min_length=3),
        license_url=_https(license_info, "url"),
        license_file_sha256=_hex64(license_info, "file_sha256"),
        license_notes=_text(license_info, "notes", min_length=10),
        benchmark_dataset=_text(benchmark, "dataset", min_length=3),
        benchmark_url=_https(benchmark, "url"),
        benchmark_sha=_sha(benchmark, "sha"),
        benchmark_license_status=_text(benchmark, "license_status", min_length=3),
        status=status,
    )


def load_evidence(path: str | Path) -> list[SourceEvidence]:
    """Load a source-evidence JSONL file."""
    items: list[SourceEvidence] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = parse_evidence(json.loads(line))
            except (json.JSONDecodeError, ManifestError, TypeError) as exc:
                raise ManifestError(f"{path}:{line_number}: {exc}") from exc
            if item.id in seen:
                raise ManifestError(f"{path}:{line_number}: duplicate evidence id {item.id}")
            seen.add(item.id)
            items.append(item)
    if not items:
        raise ManifestError(f"{path}: evidence has no rows")
    return items


def parse_execution_evidence(mapping: dict[str, Any]) -> ExecutionEvidence:
    """Validate one recorded M2 execution result without rerunning it."""
    if not isinstance(mapping, dict):
        raise ManifestError("each execution-evidence line must be a JSON object")
    run = mapping.get("run")
    runtime = mapping.get("runtime")
    base = mapping.get("base")
    fixed = mapping.get("fixed")
    source = mapping.get("source")
    test_patch = mapping.get("test_patch")
    if not all(isinstance(value, dict) for value in (run, runtime, base, fixed, source, test_patch)):
        raise ManifestError("execution evidence needs run, runtime, base, fixed, source and test_patch objects")
    applied_files = test_patch.get("applied_files")
    if not isinstance(applied_files, list) or not applied_files or not all(isinstance(item, str) and item for item in applied_files):
        raise ManifestError("test_patch.applied_files must be a non-empty list of paths")
    status = _text(mapping, "status")
    if status != _EXECUTION_STATUS:
        raise ManifestError(f"execution status must be {_EXECUTION_STATUS}")
    run_url = _https(run, "url")
    if not _RUN_URL.match(run_url):
        raise ManifestError("run.url must be a GitHub Actions run URL")
    artifacts_count = _int(run, "artifacts_count", minimum=0, maximum=100)
    if artifacts_count != 0:
        raise ManifestError("execution evidence must come from a run with no artifacts")
    if _bool(run, "benchmark_data_used"):
        raise ManifestError("accepted execution evidence must not use benchmark data")
    if _bool(run, "secrets_model_credentials_cache_artifacts"):
        raise ManifestError("accepted execution evidence must not use secrets, model credentials, cache or artifacts")
    summary_caveat = run.get("summary_caveat", "")
    if not isinstance(summary_caveat, str):
        raise ManifestError("run.summary_caveat must be a string when present")
    base_exit_code = _int(base, "exit_code", minimum=0, maximum=255)
    fixed_exit_code = _int(fixed, "exit_code", minimum=0, maximum=255)
    if base_exit_code != 1:
        raise ManifestError("base verifier evidence needs ordinary pytest failure exit code 1")
    if fixed_exit_code != 0:
        raise ManifestError("fixed verifier evidence needs exit code 0")
    return ExecutionEvidence(
        id=_text(mapping, "id", min_length=3),
        status=status,
        run_url=run_url,
        workflow_commit=_sha(run, "workflow_commit"),
        workflow_sha256=_hex64(run, "workflow_sha256"),
        runner_label=_text(run, "runner_label", min_length=5),
        job_timeout_minutes=_int(run, "job_timeout_minutes", minimum=1, maximum=120),
        benchmark_data_used=False,
        secrets_model_credentials_cache_artifacts=False,
        artifacts_count=artifacts_count,
        summary_caveat=summary_caveat.strip(),
        python_version=_text(runtime, "python", min_length=3),
        package_name=_text(runtime, "package_name", min_length=2),
        package_version=_text(runtime, "package_version", min_length=1),
        pytest_version=_text(runtime, "pytest", min_length=1),
        base_exit_code=base_exit_code,
        base_duration_s=_int(base, "duration_s", minimum=0, maximum=1200),
        base_failed_count=_int(base, "failed_count", minimum=1, maximum=1000),
        fixed_exit_code=fixed_exit_code,
        fixed_duration_s=_int(fixed, "duration_s", minimum=0, maximum=1200),
        fixed_passed_count=_int(fixed, "passed_count", minimum=1, maximum=1000),
        base_commit=_sha(source, "base_commit"),
        fixed_commit=_sha(source, "fixed_commit"),
        test_patch_identity=_text(test_patch, "identity", min_length=20),
        test_patch_source_url=_https(test_patch, "source_url"),
        test_patch_applied_files=tuple(item.strip() for item in applied_files),
        test_patch_scope=_text(test_patch, "scope", min_length=10),
    )


def load_execution_evidence(path: str | Path) -> list[ExecutionEvidence]:
    """Load an execution-evidence JSONL file."""
    items: list[ExecutionEvidence] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = parse_execution_evidence(json.loads(line))
            except (json.JSONDecodeError, ManifestError, TypeError) as exc:
                raise ManifestError(f"{path}:{line_number}: {exc}") from exc
            if item.id in seen:
                raise ManifestError(f"{path}:{line_number}: duplicate execution-evidence id {item.id}")
            seen.add(item.id)
            items.append(item)
    if not items:
        raise ManifestError(f"{path}: execution evidence has no rows")
    return items


def build_acceptance_status(
    tasks: Iterable[TaskSpec],
    evidence_rows: Iterable[SourceEvidence],
    execution_rows: Iterable[ExecutionEvidence],
) -> dict[str, Any]:
    """Summarize verified source evidence and remaining acceptance blockers."""
    task_items = list(tasks)
    source = {item.id: item for item in evidence_rows}
    execution = {item.id: item for item in execution_rows}
    task_ids = {task.id for task in task_items}
    missing_source = [task.id for task in task_items if task.id not in source]
    unknown_execution = sorted(item.id for item in execution.values() if item.id not in task_ids)
    if missing_source:
        raise ManifestError("missing source evidence for: " + ", ".join(missing_source))
    if unknown_execution:
        raise ManifestError("execution evidence does not match a task: " + ", ".join(unknown_execution))

    rows = []
    execution_summaries = []
    for task in task_items:
        source_item = source[task.id]
        execution_item = execution.get(task.id)
        if execution_item is not None:
            if execution_item.base_commit != task.source_ref:
                raise ManifestError(f"execution evidence base commit does not match task source for {task.id}")
            if execution_item.fixed_commit != source_item.fixed_commit:
                raise ManifestError(f"execution evidence fixed commit does not match source evidence for {task.id}")
            if execution_item.test_patch_source_url != source_item.test_patch_url:
                raise ManifestError(f"execution evidence test patch source does not match source evidence for {task.id}")
            if not set(execution_item.test_patch_applied_files).issubset(set(source_item.test_files)):
                raise ManifestError(f"execution evidence applied test files are outside source evidence for {task.id}")
            if execution_item.fixed_commit not in execution_item.test_patch_identity:
                raise ManifestError(f"execution evidence test patch identity does not name the fixed commit for {task.id}")
            execution_summaries.append({
                "id": execution_item.id,
                "status": execution_item.status,
                "run_url": execution_item.run_url,
                "workflow_commit": execution_item.workflow_commit,
                "workflow_sha256": execution_item.workflow_sha256,
                "runner_label": execution_item.runner_label,
                "job_timeout_minutes": execution_item.job_timeout_minutes,
                "base_exit_code": execution_item.base_exit_code,
                "fixed_exit_code": execution_item.fixed_exit_code,
                "base_failed_count": execution_item.base_failed_count,
                "fixed_passed_count": execution_item.fixed_passed_count,
                "test_patch_identity": execution_item.test_patch_identity,
                "test_patch_applied_files": list(execution_item.test_patch_applied_files),
            })
        blockers = []
        if source_item.base_relation == "ancestor":
            blockers.append("ancestor-base evidence qualification pending")
        if task.rights.status == "pending":
            blockers.append("repository and benchmark-data rights review pending")
        elif task.rights.status != "accepted":
            blockers.append(f"rights review status is {task.rights.status}")
        if execution_item is None:
            blockers.append("base-fail/fixed-pass execution evidence missing")
        blockers.append("independent task-spec review not recorded")
        rows.append({
            "id": task.id,
            "task_status": task.status,
            "rights_status": task.rights.status,
            "execution_status": execution_item.status if execution_item else "missing",
            "base_relation": source_item.base_relation,
            "ancestor_gap_commits": source_item.ancestor_gap_commits,
            "base_exit_code": execution_item.base_exit_code if execution_item else None,
            "fixed_exit_code": execution_item.fixed_exit_code if execution_item else None,
            "accepted": task.status == "accepted",
            "blockers": blockers,
        })

    summary = suite_summary(task_items)
    verified_count = sum(1 for row in rows if row["execution_status"] == _EXECUTION_STATUS)
    complete = verified_count == len(rows)
    remaining_work = [
        "accept repository and benchmark-data rights for the intended evaluation use",
        "record independent review against docs/task-spec.md for every candidate",
        "obtain separate authority before any coding-agent, model or benchmark-data run",
    ]
    ancestor_tasks = [task.id for task in task_items if source[task.id].base_relation == "ancestor"]
    if ancestor_tasks:
        remaining_work.insert(0, "resolve ancestor-base evidence qualification for: " + ", ".join(ancestor_tasks))
    return {
        "schema": "m1-acceptance-status-v0",
        "status": "upstream_source_verified_not_accepted" if complete else "execution_evidence_incomplete",
        "suite_sha256": summary["suite_sha256"],
        "execution_evidence_sha256": _digest(execution_summaries),
        "task_count": len(rows),
        "upstream_source_verified_count": verified_count,
        "accepted_count": summary["accepted_count"],
        "rights_pending_count": summary["rights_pending_count"],
        "model_or_agent_runs": 0,
        "benchmark_data_used": False,
        "remaining_acceptance_work": remaining_work,
        "tasks": rows,
        "execution": execution_summaries,
    }


def build_verification_plan(
    tasks: Iterable[TaskSpec],
    evidence_rows: Iterable[SourceEvidence],
) -> dict[str, Any]:
    """Build a deterministic base-fail/fixed-pass plan without running it."""
    task_items = list(tasks)
    evidence = {item.id: item for item in evidence_rows}
    missing = [task.id for task in task_items if task.id not in evidence]
    if missing:
        raise ManifestError("missing source evidence for: " + ", ".join(missing))
    summary = suite_summary(task_items)
    planned = []
    for task in task_items:
        item = evidence[task.id]
        expected_url = f"https://github.com/{item.repo}.git"
        if item.base_commit != task.source_ref or expected_url != task.source_url:
            raise ManifestError(f"evidence does not match task source for {task.id}")
        planned.append({
            "id": task.id,
            "status": "prepared_not_executed",
            "source": {
                "repo": item.repo,
                "url": task.source_url,
                "base_commit": task.source_ref,
                "fixed_commit": item.fixed_commit,
                "fixed_first_parent": item.fixed_first_parent,
                "base_relation": item.base_relation,
                "ancestor_gap_commits": item.ancestor_gap_commits,
                "fixed_commit_kind": item.fixed_commit_kind,
                "issue_url": item.issue_url,
                "pr_url": item.pr_url,
                "test_files": list(item.test_files),
                "implementation_files": list(item.implementation_files),
                "test_patch_url": item.test_patch_url,
            },
            "setup": list(task.setup),
            "verify": list(task.verify),
            "timeout_s": task.timeout_s,
            "expected": {
                "base": "at least one fail_to_pass test fails before the fix",
                "fixed": "all listed verifier commands pass at the fixed commit",
            },
            "provenance": {
                "task_sha256": task.summary()["task_sha256"],
                "verifier_sha256": task.verifier_sha256,
                "license_spdx": item.license_spdx,
                "license_url": item.license_url,
                "license_file_sha256": item.license_file_sha256,
                "benchmark_dataset": item.benchmark_dataset,
                "benchmark_sha": item.benchmark_sha,
                "benchmark_license_status": item.benchmark_license_status,
                "test_patch_scope": item.test_patch_scope,
                "evidence_qualification": item.evidence_qualification,
            },
        })
    plan = {
        "schema": "m1-verification-plan-v0",
        "status": "prepared_not_approved",
        "suite_sha256": summary["suite_sha256"],
        "task_count": len(planned),
        "model_access_required": False,
        "upstream_code_execution": "not_run",
        "approval_required": [
            "fresh free-runner execution approval",
            "upstream repository code and dependency installation execution",
        ],
        "tasks": planned,
    }
    plan["plan_sha256"] = _digest(plan)
    return plan
