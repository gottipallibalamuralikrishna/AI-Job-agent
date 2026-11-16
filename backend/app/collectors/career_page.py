"""Bounded public JobPosting JSON-LD collection; no login or challenge bypass."""
import hashlib
import ipaddress
import json
import re
import socket
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from app.collectors.base import BaseJobCollector
from app.services.job_location import applicant_locations


class PostingPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.links, self.buffer = [], [], None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.buffer = []
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])

    def handle_data(self, data):
        if self.buffer is not None:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.buffer is not None:
            try:
                self.scripts.append(json.loads("".join(self.buffer)))
            except ValueError:
                pass
            self.buffer = None


def postings(value):
    if isinstance(value, list):
        for item in value:
            yield from postings(item)
    elif isinstance(value, dict):
        kinds = value.get("@type", [])
        if "JobPosting" in ([kinds] if isinstance(kinds, str) else kinds):
            yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from postings(child)


def normalize_posting(item, page_url, company):
    organization = item.get("hiringOrganization") or {}
    location = item.get("jobLocation") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    address = location.get("address") or {} if isinstance(location, dict) else {}
    if isinstance(address, str):
        location_text = address
    else:
        location_text = ", ".join(str(address[k]) for k in ("addressLocality", "addressRegion", "addressCountry") if address.get(k))
    link = urljoin(page_url, item.get("url") or page_url)
    if urlparse(link).scheme not in {"http", "https"}:
        raise ValueError("Invalid application link")
    identifier = item.get("identifier")
    if isinstance(identifier, dict):
        identifier = identifier.get("value")
    posted = None
    try:
        posted = datetime.fromisoformat(item.get("datePosted", "").replace("Z", "+00:00"))
    except (ValueError, TypeError):
        pass
    return {"external_id": str(identifier or hashlib.sha256(link.encode()).hexdigest()),
            "title": item.get("title"), "company_name": organization.get("name", company) if isinstance(organization, dict) else company,
            "location": location_text or None, "description": item.get("description") or "",
            "application_url": link, "required_skills": [], "posted_at": posted,
            "remote_eligible_locations": applicant_locations(item.get("applicantLocationRequirements")),
            "work_mode": "remote" if item.get("jobLocationType") == "TELECOMMUTE" else None}


class CareerPageCollector(BaseJobCollector):
    query = "software developer"
    MAX_PAGES = 12

    def _get(self, url):
        for _ in range(4):
            parsed = urlparse(url)
            if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username:
                raise ValueError("Only public HTTP(S) pages are supported")
            addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise ValueError("Private network destinations are not supported")
            with self.client.stream("GET", url, follow_redirects=False) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers["location"])
                    continue
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 2_000_000:
                        raise ValueError("Page exceeds collection size limit")
                return bytes(data).decode("utf-8", errors="replace")
        raise ValueError("Too many redirects")

    def fetch_jobs(self, source):
        template = source.source_url or ""
        starts = [template]
        if "{query}" in template:
            starts = [template.replace("{query}", quote(query, safe=""))
                      for query in getattr(self, "queries", [self.query])]
        start = starts[0]
        origin = urlparse(start)
        robots_url = f"{origin.scheme}://{origin.netloc}/robots.txt"
        robots = RobotFileParser()
        # Fail closed when robots cannot be fetched, rather than bypassing blocks.
        robots.parse(self._get(robots_url).splitlines())
        pending, visited, jobs = starts.copy(), set(), {}
        first_error = None
        while pending and len(visited) < self.MAX_PAGES:
            url = pending.pop(0)
            if url in visited:
                continue
            visited.add(url)
            if not robots.can_fetch("JobPilotAI", url):
                if url in starts and first_error is None:
                    first_error = RuntimeError("Source disallows automated collection")
                continue
            page = PostingPage()
            try:
                page.feed(self._get(url))
            except httpx.HTTPStatusError as exc:
                if len(starts) == 1 or exc.response.status_code in {401, 403, 429}:
                    raise
                if first_error is None:
                    first_error = exc
                continue
            for script in page.scripts:
                for item in postings(script):
                    job = normalize_posting(item, url, source.name)
                    if job["title"]:
                        jobs[job["external_id"]] = job
            for href in page.links:
                link = urljoin(url, href).split("#")[0]
                if (urlparse(link).netloc == origin.netloc and link not in visited
                        and re.search(r"/(?:jobs?|careers?|positions?|opportunities)(?:/|-)", urlparse(link).path, re.I)):
                    if link not in pending and len(pending) < 100:
                        pending.append(link)
        if not jobs:
            if first_error is not None:
                raise first_error
            raise RuntimeError("No public JobPosting data found; source may require JavaScript, login, or an authorized feed")
        return list(jobs.values())
