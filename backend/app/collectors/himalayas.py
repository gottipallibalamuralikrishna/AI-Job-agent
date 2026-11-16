from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlsplit

import httpx


SOURCE_ID = "builtin:himalayas"
SEARCH_URL = "https://himalayas.app/jobs/api/search"


class HimalayasCollector:
    def fetch_jobs(self, source):
        jobs = {}
        now = datetime.now(timezone.utc)
        with httpx.Client(timeout=20) as client:
            for query in getattr(self, "queries", ["Software Developer"]):
                response = client.get(SEARCH_URL, params={
                    "country": "IN", "q": query, "sort": "relevant",
                })
                response.raise_for_status()
                for entry in response.json()["jobs"]:
                    job = self.normalize(entry, now)
                    if job:
                        jobs[job["external_id"]] = job
        return list(jobs.values())

    @staticmethod
    def normalize(entry, now):
        url = entry.get("applicationLink")
        guid = entry.get("guid")
        title = entry.get("title")
        company = entry.get("companyName")
        if not all(isinstance(value, str) and value.strip() for value in (url, guid, title, company)):
            return None
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        restrictions = entry.get("locationRestrictions") or []
        if restrictions and not any(str(country).strip().lower() in {"in", "india"} for country in restrictions):
            return None
        # The country search also enforces the provider's timezone eligibility.
        try:
            expiry = datetime.fromtimestamp(entry["expiryDate"], timezone.utc)
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            return None
        if expiry <= now:
            return None
        return {
            "external_id": sha256(guid.encode()).hexdigest(),
            "title": title.strip()[:255],
            "company_name": company.strip()[:255],
            "location": "Remote - India",
            "remote_eligible_locations": ["India"],
            "work_mode": "remote",
            "description": entry.get("description") or entry.get("excerpt") or "",
            "application_url": url,
            "source_message_url": "https://himalayas.app/",
            "expires_at": expiry,
        }

    def close(self):
        pass
