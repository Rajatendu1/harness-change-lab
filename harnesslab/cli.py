"""Local analysis CLI. This does not execute a coding agent or a sandbox."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .compare import Outcome, compare
from .run_manifest import build_run_manifest, validate_run_manifest
from .run_results import load_run_results, validate_run_results
from .tasks import ManifestError, load_suite, suite_summary
from .runtime_preflight import inspect_os_isolation, inspect_runtime
from .journal_review import summary as journal_summary
from .verification import (
    build_acceptance_status,
    build_verification_plan,
    load_evidence,
    load_execution_evidence,
    load_review_evidence,
)


def load(path: str) -> list[Outcome]:
    items = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                items.append(Outcome(**json.loads(line)))
            except (ValueError, TypeError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    return items


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    cmd = sub.add_parser("compare", help="Compare already scored, paired outcomes")
    cmd.add_argument("baseline")
    cmd.add_argument("candidate")
    cmd.add_argument("--margin", type=float, default=0.05)
    cmd.add_argument("--confidence", type=float, default=0.95)
    cmd.add_argument("--resamples", type=int, default=10000)
    cmd.add_argument("--seed", type=int, default=0)
    cmd.add_argument("--min-tasks", type=int, default=20)
    suite = sub.add_parser("validate-suite", help="Validate a task manifest without running it")
    suite.add_argument("suite")
    suite.add_argument("--min-accepted", type=int, default=0)
    plan = sub.add_parser("plan-verification", help="Prepare a base/fixed verification plan without running it")
    plan.add_argument("suite")
    plan.add_argument("evidence")
    acceptance = sub.add_parser("acceptance-status", help="Summarize execution evidence and acceptance blockers")
    acceptance.add_argument("suite")
    acceptance.add_argument("evidence")
    acceptance.add_argument("execution")
    acceptance.add_argument("review", nargs="?")
    prepare = sub.add_parser("prepare-run-manifest", help="Prepare a non-executing runner manifest contract")
    prepare.add_argument("suite")
    prepare.add_argument("evidence")
    prepare.add_argument("execution")
    prepare.add_argument("review", nargs="?")
    prepare.add_argument("--runner-name", required=True)
    prepare.add_argument("--runner-version", required=True)
    prepare.add_argument("--runner-config-sha256", required=True)
    prepare.add_argument("--trials-per-task", type=int, default=3)
    prepare.add_argument("--max-concurrency", type=int, default=1)
    validate_run = sub.add_parser("validate-run-manifest", help="Validate a manifest against the same task evidence")
    validate_run.add_argument("manifest")
    validate_run.add_argument("suite")
    validate_run.add_argument("evidence")
    validate_run.add_argument("execution")
    validate_run.add_argument("review", nargs="?")
    results = sub.add_parser("validate-run-results", help="Validate supplied runner results without executing them")
    results.add_argument("manifest")
    results.add_argument("results")
    preflight = sub.add_parser("runtime-preflight", help="Check a local prepared runtime without models or providers")
    preflight.add_argument("--python", required=True)
    preflight.add_argument("--runtime-root", required=True)
    review = sub.add_parser("review-experiment", help="Verify and summarize a saved local experiment without execution")
    review.add_argument("directory")
    args = parser.parse_args(argv)
    if args.command == "review-experiment":
        try:
            print(journal_summary(args.directory))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            parser.exit(2, f"Invalid experiment journal: {exc}\n")
        return 0
    if args.command == "runtime-preflight":
        try:
            runtime = inspect_runtime(args.python, args.runtime_root)
            isolation = inspect_os_isolation()
        except (ValueError, OSError) as exc:
            parser.exit(2, f"Invalid local runtime: {exc}\n")
        print(json.dumps({"schema": "local-runtime-preflight-v0", "runtime": runtime,
                          "isolation": isolation, "execution_authority": "none", "provider_calls": 0},
                         sort_keys=True, indent=2))
        return 0 if isolation["namespace_probe"] == "passed" else 3
    if args.command == "prepare-run-manifest":
        try:
            manifest = build_run_manifest(
                load_suite(args.suite),
                load_evidence(args.evidence),
                load_execution_evidence(args.execution),
                load_review_evidence(args.review) if args.review else None,
                runner_name=args.runner_name,
                runner_version=args.runner_version,
                runner_config_sha256=args.runner_config_sha256,
                trials_per_task=args.trials_per_task,
                max_concurrency=args.max_concurrency,
            )
        except (ManifestError, OSError) as exc:
            parser.exit(2, f"Invalid run manifest request: {exc}\n")
        print(json.dumps(manifest, sort_keys=True, indent=2))
        return 0 if manifest["status"] == "ready_not_executed" else 3
    if args.command == "validate-run-manifest":
        try:
            with Path(args.manifest).open(encoding="utf-8") as stream:
                manifest = json.load(stream)
            validate_run_manifest(
                manifest,
                load_suite(args.suite),
                load_evidence(args.evidence),
                load_execution_evidence(args.execution),
                load_review_evidence(args.review) if args.review else None,
            )
        except (ManifestError, OSError, json.JSONDecodeError) as exc:
            parser.exit(2, f"Invalid run manifest: {exc}\n")
        print(json.dumps({"schema": "m4-run-manifest-validation-v0", "status": "contract-valid", "manifest_sha256": manifest["manifest_sha256"]}, sort_keys=True, indent=2))
        return 0
    if args.command == "validate-run-results":
        try:
            with Path(args.manifest).open(encoding="utf-8") as stream:
                manifest = json.load(stream)
            summary = validate_run_results(manifest, load_run_results(args.results))
        except (ManifestError, OSError, json.JSONDecodeError) as exc:
            parser.exit(2, f"Invalid run results: {exc}\n")
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0
    if args.command == "acceptance-status":
        try:
            status = build_acceptance_status(
                load_suite(args.suite),
                load_evidence(args.evidence),
                load_execution_evidence(args.execution),
                load_review_evidence(args.review) if args.review else None,
            )
        except (ManifestError, OSError) as exc:
            parser.exit(2, f"Invalid acceptance status: {exc}\n")
        print(json.dumps(status, sort_keys=True, indent=2))
        return 0 if status["upstream_source_verified_count"] == status["task_count"] else 3
    if args.command == "plan-verification":
        try:
            prepared = build_verification_plan(load_suite(args.suite), load_evidence(args.evidence))
        except (ManifestError, OSError) as exc:
            parser.exit(2, f"Invalid verification plan: {exc}\n")
        print(json.dumps(prepared, sort_keys=True, indent=2))
        return 0
    if args.command == "validate-suite":
        try:
            summary = suite_summary(load_suite(args.suite))
        except (ManifestError, OSError) as exc:
            parser.exit(2, f"Invalid suite: {exc}\n")
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0 if summary["accepted_count"] >= args.min_accepted else 3

    try:
        result = compare(load(args.baseline), load(args.candidate),
                         margin=args.margin, confidence=args.confidence,
                         resamples=args.resamples, seed=args.seed,
                         min_tasks=args.min_tasks)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Invalid comparison: {exc}\n")
    print(json.dumps(asdict(result), sort_keys=True, indent=2))
    return {"no_detected_regression": 0, "regression": 1,
            "insufficient_evidence": 3}[result.verdict]


if __name__ == "__main__":
    raise SystemExit(main())
