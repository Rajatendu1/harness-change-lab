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


@dataclass(frozen=True)
class SourceEvidence:
    id: str
    repo: str
    base_commit: str
    fixed_merge_commit: str
    issue_url: str
    issue_title: str
    pr_url: str
    pr_title: str
    test_files: tuple[str, ...]
    license_spdx: str
    license_url: str
    license_file_sha256: str
    license_notes: str
    benchmark_dataset: str
    benchmark_url: str
    benchmark_sha: str
    benchmark_license_status: str
    status: str


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
    status = _text(mapping, "status")
    if status != _EVIDENCE_STATUS:
        raise ManifestError(f"evidence status must be {_EVIDENCE_STATUS}")
    return SourceEvidence(
        id=_text(mapping, "id", min_length=3),
        repo=_text(source, "repo", min_length=3),
        base_commit=_sha(source, "base_commit"),
        fixed_merge_commit=_sha(source, "fixed_merge_commit"),
        issue_url=_https(source, "issue_url"),
        issue_title=_text(source, "issue_title", min_length=10),
        pr_url=_https(source, "pr_url"),
        pr_title=_text(source, "pr_title", min_length=10),
        test_files=tuple(item.strip() for item in files),
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
                "fixed_merge_commit": item.fixed_merge_commit,
                "issue_url": item.issue_url,
                "pr_url": item.pr_url,
                "test_files": list(item.test_files),
            },
            "setup": list(task.setup),
            "verify": list(task.verify),
            "timeout_s": task.timeout_s,
            "expected": {
                "base": "at least one fail_to_pass test fails before the fix",
                "fixed": "all listed verifier commands pass at the fixed merge commit",
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
