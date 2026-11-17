"""Local analysis CLI. This does not execute a coding agent or a sandbox."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .compare import Outcome, compare


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
    args = parser.parse_args(argv)
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
