"""Deterministic M4 runner-manifest contract.

This module prepares and validates an execution manifest only. It never starts an
external runner, coding agent, model call, benchmark download or sandbox.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Iterable

from .tasks import ManifestError, TaskSpec
from .verification import ExecutionEvidence, SourceEvidence, build_acceptance_status

_RUNNER_NAME = re.compile(r"^[a-z0-9][a-z0-9.-]{2,63}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{key} must be a non-empty string")
    return value.strip()


def _runner(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ManifestError("runner must be an object")
    name = _text(value.get("name"), "runner.name")
    version = _text(value.get("version"), "runner.version")
    config_sha256 = _text(value.get("config_sha256"), "runner.config_sha256")
    if not _RUNNER_NAME.match(name):
        raise ManifestError("runner.name must be a lowercase slug")
    if not _RUNNER_NAME.match(version):
        raise ManifestError("runner.version must be a lowercase version slug")
    if not _HEX64.match(config_sha256):
        raise ManifestError("runner.config_sha256 must be a lowercase SHA-256 hex digest")
    return {"name": name, "version": version, "config_sha256": config_sha256}


def _trials(value: Any, key: str, *, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ManifestError(f"{key} must be an integer from {minimum} to {maximum}")
    return value


def build_run_manifest(
    tasks: Iterable[TaskSpec],
    evidence_rows: Iterable[SourceEvidence],
    execution_rows: Iterable[ExecutionEvidence],
    *,
    runner_name: str,
    runner_version: str,
    runner_config_sha256: str,
    trials_per_task: int = 3,
    max_concurrency: int = 1,
) -> dict[str, Any]:
    """Build a deterministic, non-executing runner manifest.

    A candidate suite produces `blocked_not_runnable`; the blockers are part of
    the contract. A future suite can become `ready_not_executed` only when the
    recorded tasks are accepted, rights are accepted, execution evidence matches,
    and no acceptance blocker remains. This function does not judge whether an
    external approval record is authentic.
    """
    task_items = list(tasks)
    evidence_items = list(evidence_rows)
    execution_items = list(execution_rows)
    runner = _runner({
        "name": runner_name,
        "version": runner_version,
        "config_sha256": runner_config_sha256,
    })
    trials = _trials(trials_per_task, "trials_per_task", minimum=1, maximum=20)
    concurrency = _trials(max_concurrency, "max_concurrency", minimum=1, maximum=8)
    acceptance = build_acceptance_status(task_items, evidence_items, execution_items)

    blocked_reasons: list[str] = []
    manifest_tasks = []
    for task, acceptance_row in zip(task_items, acceptance["tasks"]):
        row_blockers = list(acceptance_row["blockers"])
        for blocker in row_blockers:
            blocked_reasons.append(f"{task.id}: {blocker}")
        task_summary = task.summary()
        manifest_tasks.append({
            "id": task.id,
            "source": {"type": "git", "url": task.source_url, "ref": task.source_ref},
            "task_revision": task.task_revision,
            "task_sha256": task_summary["task_sha256"],
            "verifier_sha256": task.verifier_sha256,
            "provenance_sha256": _digest(task.provenance),
            "setup": list(task.setup),
            "verify": list(task.verify),
            "timeout_s": task.timeout_s,
            "trials": trials,
            "acceptance": {
                "task_status": acceptance_row["task_status"],
                "rights_status": acceptance_row["rights_status"],
                "execution_status": acceptance_row["execution_status"],
                "base_relation": acceptance_row["base_relation"],
                "blockers": row_blockers,
            },
        })

    if acceptance["accepted_count"] != acceptance["task_count"]:
        blocked_reasons.append("suite has unaccepted tasks")
    if acceptance["model_or_agent_runs"] != 0:
        blocked_reasons.append("recorded model or agent runs are outside this preparation contract")
    if acceptance["benchmark_data_used"]:
        blocked_reasons.append("benchmark data use is outside this preparation contract")

    status = "blocked_not_runnable" if blocked_reasons else "ready_not_executed"
    total_trial_seconds = sum(task.timeout_s * trials for task in task_items)
    manifest = {
        "schema": "m4-run-manifest-v0",
        "status": status,
        "runner": runner,
        "suite": {
            "sha256": acceptance["suite_sha256"],
            "task_count": acceptance["task_count"],
            "accepted_count": acceptance["accepted_count"],
            "upstream_source_verified_count": acceptance["upstream_source_verified_count"],
        },
        "trial_plan": {
            "trials_per_task": trials,
            "total_trials": trials * len(task_items),
            "max_concurrency": concurrency,
            "max_serial_trial_seconds": total_trial_seconds,
            "task_timeout_source": "suite timeout_s",
        },
        "execution_policy": {
            "prepare_only": True,
            "upstream_code_execution": "not_started",
            "model_access": "not_authorized_by_this_manifest",
            "benchmark_data_use": False,
            "network_access": "not_authorized_by_this_manifest",
            "secrets": "none declared",
            "artifact_upload": "none declared",
            "automatic_retry": False,
        },
        "approval_gates": [
            "all tasks accepted under source-grounded owner authority",
            "repository and applicable benchmark-data rights accepted",
            "independent task-spec review recorded",
            "separate owner authority for model, agent, network or benchmark-data execution",
        ],
        "blocked_reasons": blocked_reasons,
        "acceptance_status_sha256": _digest(acceptance),
        "tasks": manifest_tasks,
    }
    manifest["manifest_sha256"] = _digest(manifest)
    return manifest


def validate_run_manifest(
    manifest: dict[str, Any],
    tasks: Iterable[TaskSpec],
    evidence_rows: Iterable[SourceEvidence],
    execution_rows: Iterable[ExecutionEvidence],
) -> dict[str, Any]:
    """Validate a manifest by recomputing it from the same evidence."""
    if not isinstance(manifest, dict):
        raise ManifestError("run manifest must be a JSON object")
    runner = _runner(manifest.get("runner"))
    trial_plan = manifest.get("trial_plan")
    if not isinstance(trial_plan, dict):
        raise ManifestError("run manifest needs trial_plan")
    expected = build_run_manifest(
        tasks,
        evidence_rows,
        execution_rows,
        runner_name=runner["name"],
        runner_version=runner["version"],
        runner_config_sha256=runner["config_sha256"],
        trials_per_task=_trials(trial_plan.get("trials_per_task"), "trial_plan.trials_per_task", minimum=1, maximum=20),
        max_concurrency=_trials(trial_plan.get("max_concurrency"), "trial_plan.max_concurrency", minimum=1, maximum=8),
    )
    received = dict(manifest)
    received_hash = received.pop("manifest_sha256", None)
    expected_without_hash = dict(expected)
    expected_hash = expected_without_hash.pop("manifest_sha256")
    if received_hash != expected_hash or received != expected_without_hash:
        raise ManifestError("run manifest does not match the recomputed task, evidence, runner and trial contract")
    return manifest
