"""Apply the SQL METs contribution to one dataset in a project (API does the SQL)."""

from __future__ import annotations

from .client import W4HClient
from .config import contribution_slug


def dataset_id_of(row: dict) -> str:
    return str(row.get("dataset_id") or row.get("id") or "")


def dataset_in_project(project_datasets: list[dict], dataset_id: str) -> dict | None:
    want = str(dataset_id)
    for row in project_datasets:
        if dataset_id_of(row) == want:
            return row
    return None


def format_dataset_list(rows: list[dict]) -> str:
    if not rows:
        return "(none)"
    lines = []
    for row in rows:
        did = dataset_id_of(row)
        name = str(row.get("name") or "")
        lines.append(f"  {did}  {name}".rstrip())
    return "\n".join(lines)


def resolve_dataset_id(
    *,
    dataset_id: str | None,
    project_id: str | None,
    client: W4HClient,
) -> tuple[str, list[dict]]:
    """
    Target exactly one dataset. Projects may have several; never assume the first.
    If only project_id is set and that project has a single dataset, use it.
    """
    linked: list[dict] = []
    if project_id:
        linked = client.list_project_datasets(project_id)

    if dataset_id:
        if project_id and not dataset_in_project(linked, dataset_id):
            raise SystemExit(
                f"Dataset {dataset_id!r} is not linked to project {project_id}. "
                f"Linked datasets:\n{format_dataset_list(linked)}"
            )
        return str(dataset_id), linked

    if not project_id:
        raise SystemExit("Pass --dataset-id, or --project-id to list/pick a dataset.")

    if not linked:
        raise SystemExit(f"Project {project_id} has no linked datasets.")

    if len(linked) == 1:
        return dataset_id_of(linked[0]), linked

    raise SystemExit(
        "This project has multiple datasets. Pass --dataset-id with one of:\n"
        f"{format_dataset_list(linked)}"
    )


def run_on_dataset(
    dataset_id: str | None = None,
    *,
    project_id: str | None = None,
    write_back: bool = False,
    interval_minutes: float | None = None,
    limit: int | None = None,
    client: W4HClient | None = None,
) -> dict:
    """Inspect signals then bind/execute sql/compute.sql for one dataset."""
    api = client or W4HClient()
    target_id, linked = resolve_dataset_id(
        dataset_id=dataset_id,
        project_id=project_id,
        client=api,
    )
    signals = api.get_signals(target_id)
    result = api.run_sql_contribution(
        target_id,
        slug=contribution_slug(),
        write_back=write_back,
        interval_minutes=interval_minutes,
        limit=limit,
    )
    return {
        "project_id": project_id,
        "dataset_id": target_id,
        "project_datasets": linked,
        "signals": signals,
        "run": result,
    }
