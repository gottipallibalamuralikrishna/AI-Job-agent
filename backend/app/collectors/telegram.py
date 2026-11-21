
import argparse
import asyncio
import logging
import os
import re
from types import SimpleNamespace

from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError

load_dotenv()

logger = logging.getLogger(__name__)


JOB_KEYWORDS = [
    "hiring", "we are hiring", "job opening",
    "job opportunity", "vacancy", "vacancies",
    "apply now", "looking for", "open position",
    "immediate joiner", "developer required",
    "engineer required", "recruitment",
    "internship", "career opportunity",
]

ROLE_KEYWORDS = [
    "developer", "engineer", "designer", "analyst",
    "manager", "intern", "consultant", "architect",
    "tester", "frontend", "front-end", "backend",
    "back-end", "fullstack", "full-stack",
    "react", "python", "java",
]

KNOWN_SKILLS = [
    "React Native", "React", "Next.js", "JavaScript",
    "TypeScript", "HTML", "CSS", "Material UI", "MUI",
    "Redux", "MobX", "Node.js", "Express.js",
    "Python", "FastAPI", "Django", "Java",
    "Spring Boot", "C#", ".NET", "Angular", "Vue.js",
    "GraphQL", "Apollo Client", "REST API",
    "PostgreSQL", "MySQL", "MongoDB", "Firebase",
    "AWS", "Azure", "Docker", "Kubernetes",
    "Git", "CI/CD", "Tailwind CSS", "Sass",
    "Jest", "Cypress", "Playwright",
]


def get_session_path() -> str:
    backend_root = Path(__file__).resolve().parents[2]
    session_directory = backend_root / "telegram_sessions"
    session_directory.mkdir(parents=True, exist_ok=True)

    session_name = os.getenv(
        "TELEGRAM_SESSION_NAME",
        "jobpilot_telegram",
    )

    return str(session_directory / session_name)


def get_telegram_credentials() -> tuple[int, str]:
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        raise ValueError(
            "Configure TELEGRAM_API_ID and TELEGRAM_API_HASH "
            "in your backend .env file."
        )

    return int(api_id), api_hash


def get_channel_username(source_url: str) -> str:
    parsed = urlparse(source_url)

    allowed_domains = {
        "t.me",
        "www.t.me",
        "telegram.me",
        "www.telegram.me",
    }

    if parsed.netloc.lower() not in allowed_domains:
        raise ValueError(f"Invalid Telegram URL: {source_url}")

    username = parsed.path.strip("/").split("/")[0]

    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        raise ValueError(
            "Only public Telegram channel usernames are supported."
        )

    return username


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_urls(text: str) -> list[str]:
    urls = re.findall(
        r"https?://[^\s<>]+",
        text,
        flags=re.IGNORECASE,
    )

    return list(
        dict.fromkeys(
            url.rstrip(".,;:!?)\"]}")
            for url in urls
        )
    )


def extract_labelled_value(
    text: str,
    labels: list[str],
) -> str | None:
    for label in labels:
        pattern = (
            rf"(?im)^[^\w\n]*{re.escape(label)}[ \t*]*[:\-][ \t*]*(.+?)[ \t*]*$"
        )

        match = re.search(pattern, text)

        if match:
            return match.group(1).strip(" \t*")[:250] or None

    return None


def extract_title(text: str) -> str | None:
    title = extract_labelled_value(
        text,
        ["job title", "position", "role", "designation"],
    )

    if title:
        return title

    ignored = (
        "company:", "location:", "salary:",
        "experience:", "apply:", "application:",
        "skills:", "requirements:",
    )

    for line in text.splitlines()[:8]:
        line = line.strip(" \t•*-")

        if line.lower().startswith(ignored):
            continue

        if not 5 <= len(line) <= 140:
            continue

        if "http://" in line.lower() or "https://" in line.lower():
            continue

        return line

    return None


def extract_skills(text: str) -> list[str]:
    matched = []

    for skill in KNOWN_SKILLS:
        pattern = (
            r"(?<!\w)"
            + re.escape(skill.lower())
            + r"(?!\w)"
        )

        if re.search(pattern, text.lower()):
            matched.append(skill)

    return matched


def extract_experience(
    text: str,
) -> tuple[int | None, int | None]:
    match = re.search(
        r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1)), int(match.group(2))

    match = re.search(
        r"(\d+)\s*\+?\s*(?:years?|yrs?)",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        return int(match.group(1)), None

    return None, None


def extract_work_mode(text: str) -> str | None:
    normalized = text.lower()

    if "remote" in normalized or "work from home" in normalized:
        return "remote"

    if "hybrid" in normalized:
        return "hybrid"

    if "onsite" in normalized or "on-site" in normalized:
        return "onsite"

    return None


def extract_employment_type(text: str) -> str | None:
    normalized = text.lower()

    if "internship" in normalized or "intern " in normalized:
        return "internship"

    if "contract" in normalized:
        return "contract"

    if "part-time" in normalized or "part time" in normalized:
        return "part_time"

    if "freelance" in normalized:
        return "freelance"

    if "full-time" in normalized or "full time" in normalized:
        return "full_time"

    if "temporary" in normalized:
        return "temporary"

    return None


def compact_job_fields(text: str) -> dict | None:
    """Recognize title / company, location / LinkedIn job-link posts."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 3 or not 5 <= len(lines[0]) <= 140:
        return None
    if not any(role in lines[0].lower() for role in ROLE_KEYWORDS):
        return None
    parsed = urlparse(lines[2])
    host = (parsed.hostname or "").lower()
    if (parsed.scheme not in {"http", "https"}
            or not (host == "linkedin.com" or host.endswith(".linkedin.com"))
            or not re.fullmatch(r"/jobs/view/[^/]+/?", parsed.path)):
        return None
    company, separator, location = lines[1].partition(",")
    if not separator or not company.strip() or not location.strip():
        return None
    return {"title": lines[0], "company_name": company.strip(), "location": location.strip()}


def is_job_post(text: str) -> bool:
    normalized = text.lower()

    has_job_keyword = any(
        keyword in normalized for keyword in JOB_KEYWORDS
    )

    has_role = any(
        role in normalized for role in ROLE_KEYWORDS
    )

    return (has_job_keyword and has_role) or compact_job_fields(text) is not None


def normalize_phone(value: str) -> str:
    value = re.sub(r"[^\d+]", "", value)

    if value.startswith("00"):
        value = "+" + value[2:]

    return value


def extract_contacts(text: str) -> list[dict]:
    """
    Extract every publicly shared contact detail.

    Extracted contacts are not considered verified.
    """

    contacts = []
    seen = set()

    recruiter_name = extract_labelled_value(
        text,
        [
            "HR name",
            "recruiter name",
            "contact person",
            "HR contact",
        ],
    )

    def add_contact(
        contact_type: str,
        value: str,
        is_primary: bool = False,
    ):
        value = value.strip().strip(".,;")

        if not value:
            return

        key = (contact_type, value.lower())

        if key in seen:
            return

        seen.add(key)

        contacts.append({
            "contact_type": contact_type,
            "contact_value": value,
            "contact_name": recruiter_name,
            "is_primary": is_primary,
            "is_verified": False,
        })

    # Email addresses
    emails = re.findall(
        r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        text,
    )

    for email in emails:
        add_contact("email", email)

    # Phone numbers: broad international format.
    phone_candidates = re.findall(
        r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)",
        text,
    )

    for candidate in phone_candidates:
        phone = normalize_phone(candidate)

        digits = re.sub(r"\D", "", phone)

        if 8 <= len(digits) <= 15:
            add_contact("phone", phone)

    # URLs
    urls = extract_urls(text)

    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower().removeprefix("www.")

        if host == "linkedin.com" or host.endswith(".linkedin.com"):
            add_contact("linkedin", url)

        elif host in {"t.me", "telegram.me"}:
            add_contact("telegram", url)

        else:
            add_contact("application_url", url)

            # Also preserve company domains as websites.
            if not any(
                token in url.lower()
                for token in (
                    "/apply",
                    "/application",
                    "/careers",
                    "/jobs",
                )
            ):
                add_contact("website", url)

    # Telegram usernames
    usernames = re.findall(
        r"(?<![\w@])@([A-Za-z][A-Za-z0-9_]{4,31})",
        text,
    )

    for username in usernames:
        add_contact("telegram", f"@{username}")

    # Explicitly labelled application links may omit a URL scheme.
    labelled_application = extract_labelled_value(
        text,
        [
            "apply",
            "application link",
            "apply link",
            "job link",
        ],
    )

    if labelled_application:
        candidate = labelled_application.strip("<>")

        if candidate.startswith("www."):
            candidate = "https://" + candidate

        parsed = urlparse(candidate)

        if parsed.scheme in {"http", "https"} and parsed.netloc:
            add_contact(
                "application_url",
                candidate,
                is_primary=True,
            )

    return contacts


def build_job_data(
    message,
    channel_username: str,
    *,
    vacancy_title: str | None = None,
    vacancy_index: int | None = None,
) -> dict | None:
    raw_text = message.message

    if not raw_text or (vacancy_title is None and not is_job_post(raw_text)):
        return None

    title = vacancy_title or extract_title(raw_text)

    if not title:
        return None

    company = extract_labelled_value(
        raw_text,
        ["company", "company name", "organization", "organisation", "employer"],
    ) or "Not specified"

    location = extract_labelled_value(
        raw_text,
        ["location", "job location", "work location", "city"],
    )
    if vacancy_title:
        if company == "Not specified":
            parts = re.split(r"(?i)\s+at\s+", title, maxsplit=1)
            if len(parts) == 2 and parts[1].strip():
                title, company = parts[0].strip(), parts[1].strip()[:250]
        if not location:
            pin = re.search(r"(?m)^\s*📍[ \t]*([^\n|]+)", raw_text)
            if pin:
                location = pin.group(1).strip()[:250]

    compact = compact_job_fields(raw_text)
    if compact:
        title = compact["title"]
        company = compact["company_name"]
        location = compact["location"]

    experience_min, experience_max = extract_experience(
        raw_text
    )

    urls = extract_urls(raw_text)

    application_url = extract_labelled_value(
        raw_text,
        ["apply", "application link", "apply link", "job link"],
    )

    if application_url:
        application_url = application_url.strip("<>")

        if application_url.startswith("www."):
            application_url = "https://" + application_url

        parsed = urlparse(application_url)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            application_url = None

    if not application_url:
        # Use the first URL only as a fallback.
        application_url = urls[0] if urls else None

    posted_at = message.date

    if posted_at and posted_at.tzinfo is None:
        posted_at = posted_at.replace(tzinfo=timezone.utc)

    message_url = (
        f"https://t.me/{channel_username}/{message.id}"
    )

    return {
        "external_id": (
            f"telegram:{channel_username}:{message.id}"
            + (f":{vacancy_index}" if vacancy_index is not None else "")
        ),
        "title": title,
        "company_name": company,
        "location": location,
        "description": raw_text,
        "raw_source_text": raw_text,
        "source_message_url": message_url,
        "required_skills": extract_skills(raw_text),
        "experience_min": experience_min,
        "experience_max": experience_max,
        "employment_type": extract_employment_type(raw_text),
        "work_mode": extract_work_mode(raw_text),
        "application_url": application_url,
        "posted_at": posted_at,
        "is_active": True,
        "contacts": extract_contacts(raw_text),
    }


VACANCY_HEADING = re.compile(r"(?m)^[ \t*]*(?:(?:\d\ufe0f?\u20e3)+|\d+[.)])[ \t]+([^\n]+)")


def build_message_jobs(message, channel_username: str) -> list[dict]:
    body = message.message or ""
    headings = list(VACANCY_HEADING.finditer(body))
    job_headings = {
        index for index, heading in enumerate(headings)
        if any(re.search(r"\b" + re.escape(role) + r"\b", heading[1], re.I) for role in ROLE_KEYWORDS)
    }
    if len(headings) < 2 or not job_headings:
        job = build_job_data(message, channel_username)
        return [job] if job else []
    jobs = []
    for index, heading in enumerate(headings):
        if index not in job_headings:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        vacancy = SimpleNamespace(id=message.id, date=message.date, message=body[heading.start():end])
        title = heading[1].strip(" *")
        job = build_job_data(vacancy, channel_username, vacancy_title=title, vacancy_index=index + 1)
        if job:
            jobs.append(job)
    return jobs


class TelegramCollector:
    """
    Telegram collector compatible with JobIngestionService.
    """

    def __init__(self):
        self.api_id, self.api_hash = get_telegram_credentials()

        self.session_path = get_session_path()

        self.lookback_hours = max(1, int(os.getenv("TELEGRAM_LOOKBACK_HOURS", "24")))

    def collection_cutoff(self, source, now=None):
        now = now or datetime.now(timezone.utc)
        daily_window = now - timedelta(hours=self.lookback_hours)
        previous = getattr(source, "last_fetched_at", None)
        if previous is None:
            return daily_window
        if previous.tzinfo is None:
            previous = previous.replace(tzinfo=timezone.utc)
        # Re-scan the daily window for other users too; catch up after downtime.
        return min(daily_window, previous - timedelta(minutes=5))

    async def _fetch_messages(self, source) -> list[dict]:
        channel_username = get_channel_username(
            source.source_url
        )

        client = TelegramClient(
            self.session_path,
            self.api_id,
            self.api_hash,
        )

        jobs = []
        cutoff = self.collection_cutoff(source)

        try:
            await client.connect()

            if not await client.is_user_authorized():
                raise RuntimeError(
                    "Telegram session is not authorized. "
                    "Run the Telegram login command first."
                )

            entity = await client.get_entity(channel_username)

            logger.info(
                "Connected to Telegram channel @%s",
                channel_username,
            )

            async for message in client.iter_messages(
                entity,
                limit=None,
            ):
                message_date = message.date
                if message_date and message_date.tzinfo is None:
                    message_date = message_date.replace(tzinfo=timezone.utc)
                if message_date and message_date < cutoff:
                    break
                if not message.message:
                    continue

                jobs.extend(build_message_jobs(message, channel_username))

            logger.info(
                "Collected %s job messages from @%s",
                len(jobs),
                channel_username,
            )

            return jobs

        except FloodWaitError as error:
            logger.warning(
                "Telegram rate limit. Wait %s seconds.",
                error.seconds,
            )
            raise

        finally:
            await client.disconnect()

    def fetch_jobs(self, source) -> list[dict]:
        try:
            asyncio.get_running_loop()

        except RuntimeError:
            return asyncio.run(
                self._fetch_messages(source)
            )

        raise RuntimeError(
            "TelegramCollector.fetch_jobs cannot run inside "
            "an already-running asyncio event loop."
        )

    def close(self) -> None:
        return None


async def login_telegram() -> None:
    api_id, api_hash = get_telegram_credentials()

    client = TelegramClient(
        get_session_path(),
        api_id,
        api_hash,
    )

    try:
        await client.start()

        logger.info(
            "Telegram login successful. Session saved."
        )

    finally:
        await client.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--login",
        action="store_true",
        help="Authenticate Telegram and create a session.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.login:
        asyncio.run(login_telegram())
    else:
        print(
            "Use JobIngestionService to collect Telegram jobs. "
            "Run with --login to authenticate."
        )
