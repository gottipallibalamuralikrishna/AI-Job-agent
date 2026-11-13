
from datetime import datetime, timezone
from typing import Any

from app.collectors.base import BaseJobCollector


class LeverCollector(BaseJobCollector):

    def fetch_jobs(self, source) -> list[dict[str, Any]]:

        site_name = source.external_source_id

        if not site_name:
            raise ValueError(
                "Lever source requires an external_source_id (site name)"
            )

        url = (
            f"https://api.lever.co/v0/postings/"
            f"{site_name}?mode=json"
        )

        payload = self.get_json(url)

        if not isinstance(payload, list):
            raise RuntimeError(
                "Unexpected Lever response format"
            )

        normalized_jobs = []

        for item in payload:

            categories = item.get("categories") or {}

            created_at = item.get("createdAt")
            posted_at = None

            if created_at:
                posted_at = datetime.fromtimestamp(
                    created_at / 1000,
                    tz=timezone.utc,
                )

            workplace_type = item.get("workplaceType")

            work_mode = None

            if workplace_type == "remote":
                work_mode = "remote"
            elif workplace_type == "hybrid":
                work_mode = "hybrid"
            elif workplace_type == "on-site":
                work_mode = "onsite"

            commitment = categories.get("commitment", "").lower()

            employment_type = None

            if "full" in commitment:
                employment_type = "full_time"
            elif "part" in commitment:
                employment_type = "part_time"
            elif "intern" in commitment:
                employment_type = "internship"
            elif "contract" in commitment:
                employment_type = "contract"
            elif "temporary" in commitment:
                employment_type = "temporary"

            location = (
                categories.get("location")
                or ", ".join(item.get("allLocations") or [])
                or None
            )

            normalized_jobs.append({
                "external_id": str(item["id"]),
                "title": item.get("text") or "Untitled position",
                "company_name": source.name,
                "location": location,
                "description": (
                    item.get("descriptionPlain")
                    or item.get("description")
                    or ""
                ),
                "application_url": (
                    item.get("applyUrl")
                    or item.get("hostedUrl")
                ),
                "employment_type": employment_type,
                "work_mode": work_mode,
                "required_skills": [],
                "department": categories.get("department"),
                "posted_at": posted_at,
            })

        return normalized_jobs
