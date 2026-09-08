"""CLI for RAG pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import run_full_refresh
from .registry import get_last_runs


def main() -> None:
    p = argparse.ArgumentParser(description="RAG pipeline CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="Run full refresh")
    run_p.add_argument("--force", action="store_true")
    run_p.add_argument("--week", type=str, default=None)
    sub.add_parser("status", help="Show last runs")
    diff_p = sub.add_parser("diff", help="Diff manifests")
    diff_p.add_argument("--week", type=str, required=True)

    args = p.parse_args()
    if args.cmd == "run":
        res = run_full_refresh(force=args.force, week=args.week)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.cmd == "status":
        runs = get_last_runs(limit=10)
        print(json.dumps(runs, ensure_ascii=False, indent=2, default=str))
    elif args.cmd == "diff":
        manifest = Path(f"data/rag/manifests/{args.week}.json")
        if not manifest.exists():
            print(f"Manifest not found: {manifest}")
            return
        print(manifest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
