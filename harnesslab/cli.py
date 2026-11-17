"""Local analysis CLI. This does not execute a coding agent or a sandbox."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .compare import Outcome, compare
from .tasks import ManifestError, load_suite, suite_summary
from .verification import build_verification_plan, load_evidence


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
    args = parser.parse_args(argv)
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
