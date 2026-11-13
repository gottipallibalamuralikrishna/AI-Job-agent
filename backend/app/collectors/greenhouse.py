
from html import unescape
from typing import Any

from app.collectors.base import BaseJobCollector


class GreenhouseCollector(BaseJobCollector):

    def fetch_jobs(self, source) -> list[dict[str, Any]]:

        board_token = source.external_source_id

        if not board_token:
            raise ValueError(
                "Greenhouse source requires an external_source_id (board token)"
            )

        url = (
            f"https://boards-api.greenhouse.io/v1/"
            f"boards/{board_token}/jobs?content=true"
        )

        payload = self.get_json(url)
        raw_jobs = payload.get("jobs", [])

        normalized_jobs = []

        for item in raw_jobs:

            location = item.get("location") or {}
            departments = item.get("departments") or []

            description = item.get("content") or ""

            normalized_jobs.append({
                "external_id": str(item["id"]),
                "title": item.get("title") or "Untitled position",
                "company_name": source.name,
                "location": location.get("name"),
                "description": unescape(description),
                "application_url": item.get("absolute_url"),
                "employment_type": None,
                "work_mode": None,
                "required_skills": [],
                "department": ", ".join(
                    department.get("name", "")
                    for department in departments
                    if department.get("name")
                ) or None,
                "posted_at": None,
            })

        return normalized_jobs
