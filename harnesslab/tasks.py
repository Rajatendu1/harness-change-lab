"""Task-suite manifest loading and deterministic identity checks."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

_ID = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")
_SHA = re.compile(r"^[0-9a-f]{40}$")
_TASK_STATUSES = {"candidate", "accepted"}
_RIGHTS_STATUSES = {"pending", "accepted", "rejected"}


class ManifestError(ValueError):
    """Raised when a task suite manifest is unsafe or incomplete."""


@dataclass(frozen=True)
class RightsReview:
    status: str
    license: str
    license_url: str
    data_use: str
    notes: str


@dataclass(frozen=True)
class TaskSpec:
    id: str
    status: str
    source_url: str
    source_ref: str
    issue: str
    setup: tuple[str, ...]
    verify: tuple[str, ...]
    timeout_s: int
    tags: tuple[str, ...]
    provenance: dict[str, Any]
    rights: RightsReview

    @property
    def task_revision(self) -> str:
        return self.source_ref

    @property
    def verifier_sha256(self) -> str:
        return _digest({
            "verify": list(self.verify),
            "timeout_s": self.timeout_s,
        })

    @property
    def task_sha256(self) -> str:
        return _digest({
            "id": self.id,
            "status": self.status,
            "source": {"type": "git", "url": self.source_url, "ref": self.source_ref},
            "issue": self.issue,
            "setup": list(self.setup),
            "verify": list(self.verify),
            "timeout_s": self.timeout_s,
            "tags": list(self.tags),
            "provenance": self.provenance,
            "rights": {
                "status": self.rights.status,
                "license": self.rights.license,
                "license_url": self.rights.license_url,
                "data_use": self.rights.data_use,
                "notes": self.rights.notes,
            },
        })

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "source_url": self.source_url,
            "task_revision": self.task_revision,
            "verifier_sha256": self.verifier_sha256,
            "task_sha256": self.task_sha256,
            "rights_status": self.rights.status,
        }


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _text(mapping: dict[str, Any], key: str, *, min_length: int = 1) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or len(value.strip()) < min_length:
        raise ManifestError(f"{key} must be a string of at least {min_length} characters")
    return value.strip()


def _commands(mapping: dict[str, Any], key: str) -> tuple[str, ...]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise ManifestError(f"{key} must be a non-empty list of commands")
    commands = []
    for command in value:
        if not isinstance(command, str) or not command.strip():
            raise ManifestError(f"{key} commands must be non-empty strings")
        if any(token in command for token in ("$", "`", "${", "GH_TOKEN", "GITHUB_TOKEN")):
            raise ManifestError(f"{key} command contains a shell-expansion or credential marker")
        commands.append(command.strip())
    return tuple(commands)


def _tags(mapping: dict[str, Any]) -> tuple[str, ...]:
    value = mapping.get("tags")
    if not isinstance(value, list) or not value:
        raise ManifestError("tags must be a non-empty list")
    tags = []
    for tag in value:
        if not isinstance(tag, str) or not _ID.match(tag):
            raise ManifestError("each tag must be a lowercase slug")
        tags.append(tag)
    if len(set(tags)) != len(tags):
        raise ManifestError("tags must not repeat")
    return tuple(tags)


def _source(mapping: dict[str, Any]) -> tuple[str, str]:
    source = mapping.get("source")
    if not isinstance(source, dict):
        raise ManifestError("source must be an object")
    if source.get("type") != "git":
        raise ManifestError("source.type must be git")
    url = _text(source, "url", min_length=8)
    if not (url.startswith("https://github.com/") and url.endswith(".git")):
        raise ManifestError("source.url must be a public GitHub HTTPS clone URL ending in .git")
    ref = _text(source, "ref")
    if not _SHA.match(ref):
        raise ManifestError("source.ref must be a lowercase 40-character commit SHA")
    return url, ref


def _provenance(mapping: dict[str, Any]) -> dict[str, Any]:
    value = mapping.get("provenance")
    if not isinstance(value, dict) or not value:
        raise ManifestError("provenance must be a non-empty object")
    tests = value.get("fail_to_pass")
    if not isinstance(tests, list) or not tests or not all(isinstance(item, str) and item for item in tests):
        raise ManifestError("provenance.fail_to_pass must list the failing verification tests")

    legacy_keys = {"benchmark", "instance_id", "dataset_url"}
    if legacy_keys & set(value):
        for key in ("benchmark", "instance_id", "dataset_url"):
            _text(value, key, min_length=3)
        commit = value.get("environment_setup_commit")
        if commit is not None and (not isinstance(commit, str) or not _SHA.match(commit)):
            raise ManifestError("provenance.environment_setup_commit must be a commit SHA when present")
        return value

    for key in ("base_commit", "fixed_commit", "fixed_first_parent"):
        commit = _text(value, key, min_length=40)
        if not _SHA.match(commit):
            raise ManifestError(f"provenance.{key} must be a lowercase 40-character commit SHA")
    if value.get("base_relation") != "direct-parent":
        raise ManifestError("direct-upstream provenance needs base_relation direct-parent")
    if value["base_commit"] != value["fixed_first_parent"]:
        raise ManifestError("direct-upstream provenance needs base_commit equal to fixed_first_parent")
    for key in ("issue_url", "selection_source"):
        _text(value, key, min_length=10)
    pr_url = value.get("pr_url", value.get("fix_pr_url"))
    if not isinstance(pr_url, str) or len(pr_url.strip()) < 10:
        raise ManifestError("direct-upstream provenance needs pr_url or fix_pr_url")
    if not value["issue_url"].startswith("https://") or not pr_url.startswith("https://"):
        raise ManifestError("direct-upstream issue and pull-request URLs must be HTTPS URLs")
    test_files = value.get("test_files")
    if not isinstance(test_files, list) or not test_files or not all(isinstance(item, str) and item for item in test_files):
        raise ManifestError("direct-upstream provenance.test_files must list changed test files")
    return value


def _rights(mapping: dict[str, Any]) -> RightsReview:
    value = mapping.get("rights")
    if not isinstance(value, dict):
        raise ManifestError("rights must be an object")
    status = _text(value, "status")
    if status not in _RIGHTS_STATUSES:
        raise ManifestError("rights.status must be pending, accepted or rejected")
    review = RightsReview(
        status=status,
        license=_text(value, "license", min_length=3),
        license_url=_text(value, "license_url", min_length=3),
        data_use=_text(value, "data_use", min_length=10),
        notes=_text(value, "notes", min_length=10),
    )
    if status == "accepted" and not review.license_url.startswith("https://"):
        raise ManifestError("accepted rights need an HTTPS license_url")
    return review


def parse_task(mapping: dict[str, Any]) -> TaskSpec:
    """Validate one task manifest object."""
    if not isinstance(mapping, dict):
        raise ManifestError("each task line must be a JSON object")
    task_id = _text(mapping, "id", min_length=3)
    if not _ID.match(task_id):
        raise ManifestError("id must be a lowercase slug of 3-64 characters")
    status = _text(mapping, "status")
    if status not in _TASK_STATUSES:
        raise ManifestError("status must be candidate or accepted")
    source_url, source_ref = _source(mapping)
    timeout_s = mapping.get("timeout_s")
    if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or not 60 <= timeout_s <= 3600:
        raise ManifestError("timeout_s must be an integer from 60 to 3600")
    rights = _rights(mapping)
    if status == "accepted" and rights.status != "accepted":
        raise ManifestError("an accepted task needs accepted rights")
    if rights.status == "rejected" and status != "candidate":
        raise ManifestError("a rights-rejected task cannot be accepted")
    return TaskSpec(
        id=task_id,
        status=status,
        source_url=source_url,
        source_ref=source_ref,
        issue=_text(mapping, "issue", min_length=20),
        setup=_commands(mapping, "setup"),
        verify=_commands(mapping, "verify"),
        timeout_s=timeout_s,
        tags=_tags(mapping),
        provenance=_provenance(mapping),
        rights=rights,
    )


def load_suite(path: str | Path) -> list[TaskSpec]:
    """Load and validate a JSONL task suite."""
    tasks: list[TaskSpec] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                task = parse_task(raw)
            except (json.JSONDecodeError, ManifestError, TypeError) as exc:
                raise ManifestError(f"{path}:{line_number}: {exc}") from exc
            if task.id in seen:
                raise ManifestError(f"{path}:{line_number}: duplicate task id {task.id}")
            seen.add(task.id)
            tasks.append(task)
    if not tasks:
        raise ManifestError(f"{path}: suite has no tasks")
    return tasks


def suite_summary(tasks: Iterable[TaskSpec]) -> dict[str, Any]:
    """Return a deterministic suite summary without executing any task."""
    items = [task.summary() for task in tasks]
    accepted = sum(1 for task in items if task["status"] == "accepted")
    rights_pending = sum(1 for task in items if task["rights_status"] == "pending")
    digest = _digest(items)
    return {
        "suite_sha256": digest,
        "task_count": len(items),
        "accepted_count": accepted,
        "candidate_count": len(items) - accepted,
        "rights_pending_count": rights_pending,
        "tasks": items,
    }
