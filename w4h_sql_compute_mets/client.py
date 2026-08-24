"""HTTP client: project datasets, table metadata, YAML-bound SQL run. No local SQL."""

from __future__ import annotations

import requests

from .config import api_base, contribution_slug, require_api_key


def _raise_for_status(resp: requests.Response) -> None:
    if resp.ok:
        return
    detail = resp.text
    try:
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("error"):
            detail = str(payload["error"])
    except ValueError:
        pass
    method = resp.request.method if resp.request else "GET"
    url = resp.url
    raise requests.HTTPError(f"{resp.status_code} {method} {url}: {detail}", response=resp)


class W4HClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or api_base()).rstrip("/")
        key = (api_key or require_api_key()).strip()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-W4H-API-Key": key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def get_project(self, project_id: str) -> dict:
        url = f"{self.base_url}/projects/{project_id}"
        resp = self.session.get(url, timeout=60)
        _raise_for_status(resp)
        return resp.json()

    def list_project_datasets(self, project_id: str) -> list[dict]:
        payload = self.get_project(project_id)
        rows = payload.get("datasets") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []
        return rows

    def get_dataset(self, dataset_id: str) -> dict:
        url = f"{self.base_url}/datasets/{dataset_id}"
        resp = self.session.get(url, timeout=60)
        _raise_for_status(resp)
        return resp.json()

    def get_signals(self, dataset_id: str) -> dict:
        """Table / GeoMTS mapping metadata for one dataset."""
        url = f"{self.base_url}/datasets/{dataset_id}/signals"
        resp = self.session.get(url, timeout=60)
        _raise_for_status(resp)
        return resp.json()

    def run_sql_contribution(
        self,
        dataset_id: str,
        *,
        slug: str | None = None,
        write_back: bool = False,
        interval_minutes: float | None = None,
        limit: int | None = None,
    ) -> dict:
        """Ask the API to bind and execute a curated SQL contribution against this dataset."""
        url = f"{self.base_url}/datasets/{dataset_id}/contributions/{slug or contribution_slug()}/sql"
        payload: dict = {"write_back": write_back}
        if interval_minutes is not None:
            payload["interval_minutes"] = interval_minutes
        if limit is not None:
            payload["limit"] = limit
        resp = self.session.post(url, json=payload, timeout=300)
        _raise_for_status(resp)
        return resp.json()
