"""Validate supplied runner results against an M4 manifest.

This module only checks the integrity and completeness of result records that
were produced elsewhere. It does not start, replay or authenticate a runner.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .tasks import ManifestError

_RUN_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{2,63}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class RunResult:
    run_id: str
    manifest_sha256: str
    task_id: str
    task_revision: str
    task_sha256: str
    verifier_sha256: str
    trial_index: int
    runner_name: str
    runner_version: str
    runner_config_sha256: str
    base_exit_code: int
    base_duration_s: int
    base_failed_count: int
    fixed_exit_code: int
    fixed_duration_s: int
    fixed_passed_count: int
    model_access: bool
    benchmark_data_used: bool
    secrets_used: bool
    artifact_upload_count: int
    automatic_retry: bool


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(mapping: dict[str, Any], key: str, *, min_length: int = 1) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or len(value.strip()) < min_length:
        raise ManifestError(f"result {key} must be a string of at least {min_length} characters")
    return value.strip()


def _hex64(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping, key, min_length=64)
    if not _HEX64.match(value):
        raise ManifestError(f"result {key} must be a lowercase SHA-256 hex digest")
    return value


def _sha(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping, key, min_length=40)
    if not _SHA.match(value):
        raise ManifestError(f"result {key} must be a lowercase commit SHA")
    return value


def _bool(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ManifestError(f"result {key} must be a boolean")
    return value


def _int(mapping: dict[str, Any], key: str, *, minimum: int, maximum: int) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ManifestError(f"result {key} must be an integer from {minimum} to {maximum}")
    return value


def parse_run_result(mapping: dict[str, Any]) -> RunResult:
    """Validate one supplied result row without trusting its provenance."""
    if not isinstance(mapping, dict):
        raise ManifestError("each result line must be a JSON object")
    if mapping.get("schema") != "m6-run-result-v0":
        raise ManifestError("result schema must be m6-run-result-v0")
    task = mapping.get("task")
    runner = mapping.get("runner")
    base = mapping.get("base")
    fixed = mapping.get("fixed")
    policy = mapping.get("policy")
    if not all(isinstance(value, dict) for value in (task, runner, base, fixed, policy)):
        raise ManifestError("result needs task, runner, base, fixed and policy objects")
    if mapping.get("status") != "completed":
        raise ManifestError("only completed result rows can be validated")
    run_id = _text(mapping, "run_id", min_length=3)
    if not _RUN_ID.match(run_id):
        raise ManifestError("run_id must be a lowercase slug")
    base_exit_code = _int(base, "exit_code", minimum=0, maximum=255)
    fixed_exit_code = _int(fixed, "exit_code", minimum=0, maximum=255)
    if base_exit_code != 1:
        raise ManifestError("base result needs ordinary pytest failure exit code 1")
    if fixed_exit_code != 0:
        raise ManifestError("fixed result needs exit code 0")
    return RunResult(
        run_id=run_id,
        manifest_sha256=_hex64(mapping, "manifest_sha256"),
        task_id=_text(task, "id", min_length=3),
        task_revision=_sha(task, "revision"),
        task_sha256=_hex64(task, "task_sha256"),
        verifier_sha256=_hex64(task, "verifier_sha256"),
        trial_index=_int(mapping, "trial_index", minimum=1, maximum=20),
        runner_name=_text(runner, "name", min_length=3),
        runner_version=_text(runner, "version", min_length=3),
        runner_config_sha256=_hex64(runner, "config_sha256"),
        base_exit_code=base_exit_code,
        base_duration_s=_int(base, "duration_s", minimum=0, maximum=3600),
        base_failed_count=_int(base, "failed_count", minimum=1, maximum=1000),
        fixed_exit_code=fixed_exit_code,
        fixed_duration_s=_int(fixed, "duration_s", minimum=0, maximum=3600),
        fixed_passed_count=_int(fixed, "passed_count", minimum=1, maximum=1000),
        model_access=_bool(policy, "model_access"),
        benchmark_data_used=_bool(policy, "benchmark_data_used"),
        secrets_used=_bool(policy, "secrets_used"),
        artifact_upload_count=_int(policy, "artifact_upload_count", minimum=0, maximum=100),
        automatic_retry=_bool(policy, "automatic_retry"),
    )


def load_run_results(path: str | Path) -> list[RunResult]:
    """Load a supplied result JSONL file."""
    items: list[RunResult] = []
    seen: set[tuple[str, int]] = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = parse_run_result(json.loads(line))
            except (json.JSONDecodeError, ManifestError, TypeError) as exc:
                raise ManifestError(f"{path}:{line_number}: {exc}") from exc
            key = (item.task_id, item.trial_index)
            if key in seen:
                raise ManifestError(f"{path}:{line_number}: duplicate task/trial result {item.task_id}/{item.trial_index}")
            seen.add(key)
            items.append(item)
    if not items:
        raise ManifestError(f"{path}: result file has no rows")
    return items


def validate_run_results(manifest: dict[str, Any], result_rows: Iterable[RunResult]) -> dict[str, Any]:
    """Validate complete supplied results against a ready M4 manifest.

    A valid result means the records match the manifest contract. It does not
    prove that an external run happened, and it does not accept the suite.
    """
    if not isinstance(manifest, dict) or manifest.get("schema") != "m4-run-manifest-v0":
        raise ManifestError("run results need an m4-run-manifest-v0 manifest")
    if manifest.get("status") != "ready_not_executed":
        raise ManifestError("run results cannot be validated against a blocked or already-executed manifest")
    manifest_hash = manifest.get("manifest_sha256")
    if not isinstance(manifest_hash, str) or not _HEX64.match(manifest_hash):
        raise ManifestError("manifest needs a lowercase manifest_sha256")
    runner = manifest.get("runner")
    tasks = manifest.get("tasks")
    if not isinstance(runner, dict) or not isinstance(tasks, list) or not tasks:
        raise ManifestError("manifest needs runner and tasks")
    expected_tasks = {task.get("id"): task for task in tasks if isinstance(task, dict)}
    if len(expected_tasks) != len(tasks):
        raise ManifestError("manifest task ids must be unique objects")
    expected_pairs = {
        (task_id, trial)
        for task_id, task in expected_tasks.items()
        for trial in range(1, task.get("trials", 0) + 1)
    }
    rows = list(result_rows)
    seen: set[tuple[str, int]] = set()
    run_ids = set()
    normalized = []
    for row in rows:
        key = (row.task_id, row.trial_index)
        if key in seen:
            raise ManifestError(f"duplicate task/trial result {row.task_id}/{row.trial_index}")
        seen.add(key)
        if key not in expected_pairs:
            raise ManifestError(f"result task/trial is outside the manifest: {row.task_id}/{row.trial_index}")
        task = expected_tasks[row.task_id]
        if row.manifest_sha256 != manifest_hash:
            raise ManifestError(f"result manifest hash does not match for {row.task_id}")
        if row.task_revision != task.get("task_revision") or row.task_sha256 != task.get("task_sha256") or row.verifier_sha256 != task.get("verifier_sha256"):
            raise ManifestError(f"result task identity does not match for {row.task_id}")
        if row.runner_name != runner.get("name") or row.runner_version != runner.get("version") or row.runner_config_sha256 != runner.get("config_sha256"):
            raise ManifestError(f"result runner identity does not match for {row.task_id}")
        if row.base_duration_s > task.get("timeout_s", 0) or row.fixed_duration_s > task.get("timeout_s", 0):
            raise ManifestError(f"result duration exceeds the task timeout for {row.task_id}")
        if row.model_access or row.benchmark_data_used or row.secrets_used or row.automatic_retry or row.artifact_upload_count != 0:
            raise ManifestError(f"result policy violates the manifest boundary for {row.task_id}")
        run_ids.add(row.run_id)
        normalized.append({
            "run_id": row.run_id,
            "manifest_sha256": row.manifest_sha256,
            "task_id": row.task_id,
            "task_revision": row.task_revision,
            "task_sha256": row.task_sha256,
            "verifier_sha256": row.verifier_sha256,
            "trial_index": row.trial_index,
            "base": {
                "exit_code": row.base_exit_code,
                "duration_s": row.base_duration_s,
                "failed_count": row.base_failed_count,
            },
            "fixed": {
                "exit_code": row.fixed_exit_code,
                "duration_s": row.fixed_duration_s,
                "passed_count": row.fixed_passed_count,
            },
        })
    missing = sorted(expected_pairs - seen)
    if missing:
        raise ManifestError("missing task/trial results: " + ", ".join(f"{task}/{trial}" for task, trial in missing))
    if len(run_ids) != 1:
        raise ManifestError("all result rows need one consistent run_id")
    task_summaries = []
    for task_id, task in sorted(expected_tasks.items()):
        task_rows = [row for row in normalized if row["task_id"] == task_id]
        task_summaries.append({
            "id": task_id,
            "task_revision": task["task_revision"],
            "task_sha256": task["task_sha256"],
            "verifier_sha256": task["verifier_sha256"],
            "trials": len(task_rows),
            "base_failed_count": sum(row["base"]["failed_count"] for row in task_rows),
            "fixed_passed_count": sum(row["fixed"]["passed_count"] for row in task_rows),
        })
    return {
        "schema": "m6-run-result-validation-v0",
        "status": "results_contract_valid",
        "run_id": next(iter(run_ids)),
        "manifest_sha256": manifest_hash,
        "task_count": len(expected_tasks),
        "trial_count": len(normalized),
        "model_or_agent_runs": 0,
        "benchmark_data_used": False,
        "artifact_upload_count": 0,
        "automatic_retries": 0,
        "tasks": task_summaries,
        "results_sha256": _digest(normalized),
        "evidence_scope": "supplied result records only; the harness did not execute, replay or authenticate the run",
    }
