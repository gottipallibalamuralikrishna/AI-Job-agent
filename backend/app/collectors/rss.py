
import calendar
import ipaddress
import logging

from datetime import datetime, timezone
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser

from app.collectors.base import BaseJobCollector


logger = logging.getLogger(__name__)


class RSSCollector(BaseJobCollector):
    """
    Collects publicly accessible job listings from RSS and Atom feeds.
    """

    def validate_feed_url(self, feed_url: str) -> None:
        """
        Basic URL validation to reject unsupported schemes
        and obvious local/private IP destinations.
        """

        parsed_url = urlparse(feed_url)

        if parsed_url.scheme not in {"http", "https"}:
            raise ValueError(
                "RSS feed URL must use HTTP or HTTPS."
            )

        if not parsed_url.hostname:
            raise ValueError("Invalid RSS feed URL.")

        hostname = parsed_url.hostname.lower()

        if hostname in {"localhost", "localhost.localdomain"}:
            raise ValueError(
                "Localhost is not allowed as an RSS feed URL."
            )

        try:
            ip_address = ipaddress.ip_address(hostname)

            if (
                ip_address.is_private
                or ip_address.is_loopback
                or ip_address.is_link_local
                or ip_address.is_reserved
            ):
                raise ValueError(
                    "Private or local IP addresses are not allowed."
                )

        except ValueError as exc:
            # Re-raise our validation error, but allow ordinary
            # domain names that are not IP addresses.
            if "not allowed" in str(exc):
                raise

    @staticmethod
    def get_entry_value(entry, *field_names):
        """
        Return the first non-empty value from an RSS entry.
        """

        for field_name in field_names:

            value = entry.get(field_name)

            if value:
                return value

        return None

    @staticmethod
    def extract_description(entry) -> str:
        """
        Extract description/content from different RSS formats.
        """

        description = (
            entry.get("description")
            or entry.get("summary")
            or ""
        )

        content = entry.get("content") or []

        if content and isinstance(content, list):

            content_value = content[0].get("value")

            if content_value:
                description = content_value

        return unescape(str(description))

    @staticmethod
    def extract_published_date(entry):
        """
        Convert RSS published/updated date into UTC datetime.
        """

        parsed_date = (
            entry.get("published_parsed")
            or entry.get("updated_parsed")
        )

        if not parsed_date:
            return None

        try:
            timestamp = calendar.timegm(parsed_date)

            return datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            )

        except (ValueError, TypeError, OverflowError):
            return None

    def fetch_jobs(self, source) -> list[dict[str, Any]]:
        """
        Fetch and normalize jobs from an RSS or Atom feed.

        source.source_url must contain the feed URL.
        """

        feed_url = source.source_url

        if not feed_url:
            raise ValueError(
                "RSS source requires a source_url."
            )

        self.validate_feed_url(feed_url)

        try:

            response = self.client.get(feed_url)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

        except Exception as exc:

            logger.exception(
                "Unable to fetch RSS feed: %s",
                feed_url,
            )

            raise RuntimeError(
                "Unable to fetch the RSS feed."
            ) from exc

        entries = feed.entries or []

        if not entries:

            if getattr(feed, "bozo", False):
                raise RuntimeError(
                    "The RSS feed is invalid or could not be parsed."
                )

            logger.warning(
                "RSS feed contains no entries: %s",
                feed_url,
            )

            return []

        normalized_jobs = []

        for entry in entries:

            try:

                title = self.get_entry_value(
                    entry,
                    "title",
                )

                if not title:
                    continue

                # RSS feeds commonly use guid or id.
                external_id = self.get_entry_value(
                    entry,
                    "id",
                    "guid",
                    "link",
                )

                link = self.get_entry_value(
                    entry,
                    "link",
                )

                if not external_id and not link:
                    continue

                application_url = (
                    urljoin(feed_url, link)
                    if link
                    else None
                )

                description = self.extract_description(entry)

                published_at = self.extract_published_date(
                    entry
                )

                # Company information is optional in RSS feeds.
                company_name = self.get_entry_value(
                    entry,
                    "company",
                    "employer",
                    "organization",
                )

                # Use the configured source name as a fallback.
                if not company_name:
                    company_name = source.name

                location = self.get_entry_value(
                    entry,
                    "location",
                    "job_location",
                    "region",
                )

                normalized_job = {
                    "external_id": str(external_id),

                    "title": str(title).strip(),

                    "company_name": str(company_name).strip(),

                    "location": (
                        str(location).strip()
                        if location
                        else None
                    ),

                    "description": description,

                    "application_url": application_url,

                    "employment_type": None,

                    "work_mode": None,

                    "required_skills": [],

                    "department": None,

                    "posted_at": published_at,
                }

                normalized_jobs.append(normalized_job)

            except Exception:

                logger.exception(
                    "Unable to normalize RSS entry: %s",
                    entry.get("title"),
                )

                continue

        logger.info(
            "Normalized %s jobs from RSS source %s",
            len(normalized_jobs),
            source.name,
        )

        return normalized_jobs
