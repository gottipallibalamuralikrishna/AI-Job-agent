
from abc import ABC, abstractmethod
from typing import Any

import httpx


class BaseJobCollector(ABC):

    TIMEOUT = 30.0

    def __init__(self):
        self.client = httpx.Client(
            timeout=self.TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": "JobPilotAI/1.0 (public job board integration)"
            },
        )

    @abstractmethod
    def fetch_jobs(self, source) -> list[dict[str, Any]]:
        """Fetch and normalize jobs from a registered source."""
        raise NotImplementedError

    def get_json(self, url: str) -> Any:
        try:
            response = self.client.get(url)
            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Source request timed out: {url}"
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Source returned HTTP {exc.response.status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise RuntimeError(
                "Unable to connect to job source"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "Job source returned invalid JSON"
            ) from exc

    def close(self):
        self.client.close()
