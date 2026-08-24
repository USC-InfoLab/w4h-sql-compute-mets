"""CLI: list project datasets, inspect signals, run SQL METs via the API."""

from __future__ import annotations

import argparse
import json
import sys

from .client import W4HClient
from .config import dataset_id as env_dataset_id
from .config import project_id as env_project_id
from .run import resolve_dataset_id, run_on_dataset


def _print_datasets(rows: list[dict]) -> None:
    if not rows:
        print("No datasets linked to this project.")
        return
    print(f"{'dataset_id':<36}  name")
    for row in rows:
        did = str(row.get("dataset_id") or row.get("id") or "")
        name = str(row.get("name") or "")
        print(f"{did:<36}  {name}")


def _cmd_datasets(args: argparse.Namespace) -> int:
    if not args.project_id:
        raise SystemExit("Pass --project-id (or set W4H_PROJECT_ID)")
    rows = W4HClient().list_project_datasets(args.project_id)
    _print_datasets(rows)
    return 0


def _cmd_signals(args: argparse.Namespace) -> int:
    api = W4HClient()
    target_id, _ = resolve_dataset_id(
        dataset_id=args.dataset_id,
        project_id=args.project_id,
        client=api,
    )
    payload = api.get_signals(target_id)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def _cmd_compute(args: argparse.Namespace) -> int:
    result = run_on_dataset(
        args.dataset_id,
        project_id=args.project_id or None,
        write_back=args.write_back,
        interval_minutes=args.interval_minutes,
        limit=None if args.write_back else args.limit,
    )
    run = result["run"]
    print(f"dataset_id={result['dataset_id']}")
    if run.get("write_back"):
        print(
            f"wrote {run.get('physical_schema')}.{run.get('physical_table')} "
            f"inserted={run.get('inserted')} interval={run.get('interval_minutes')}"
        )
        return 0
    rows = run.get("rows") or []
    cols = run.get("columns") or []
    print(f"preview rows={run.get('row_count')} interval={run.get('interval_minutes')}")
    if cols:
        print(",".join(cols))
    for row in rows[: args.limit]:
        if isinstance(row, dict) and cols:
            print(",".join(str(row.get(c, "")) for c in cols))
        else:
            print(row)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run YAML-bound SQL METs against one dataset in a W4H project. "
            "The API binds and executes sql/compute.sql; this CLI does not run SQL locally."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ds = sub.add_parser("datasets", help="List datasets linked to a project")
    p_ds.add_argument("--project-id", default=env_project_id() or None)

    p_sig = sub.add_parser("signals", help="Show table metadata (GET /datasets/:id/signals)")
    p_sig.add_argument("--project-id", default=env_project_id() or None)
    p_sig.add_argument("--dataset-id", default=env_dataset_id() or None)

    p_compute = sub.add_parser(
        "compute",
        help="Preview or materialize METs via POST /datasets/:id/contributions/:slug/sql",
    )
    p_compute.add_argument("--project-id", default=env_project_id() or None)
    p_compute.add_argument("--dataset-id", default=env_dataset_id() or None)
    p_compute.add_argument(
        "--interval-minutes",
        type=float,
        default=None,
        help="Override native row interval when mapping has no sampling_interval (5=ICDE, 1=Fitbit)",
    )
    p_compute.add_argument("--limit", type=int, default=20, help="Preview row cap (ignored with --write-back)")
    p_compute.add_argument(
        "--write-back",
        action="store_true",
        help="Materialize mets_computed on the dataset (Admin). Off by default = preview.",
    )

    args = parser.parse_args(argv)
    try:
        if args.command == "datasets":
            return _cmd_datasets(args)
        if args.command == "signals":
            return _cmd_signals(args)
        if args.command == "compute":
            return _cmd_compute(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
