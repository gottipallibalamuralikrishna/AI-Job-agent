
# app/services/job_matching_service.py

import re
from html import unescape
from html.parser import HTMLParser
from typing import Any


class HTMLTextExtractor(HTMLParser):
    """Extract readable text from an HTML job description."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self, html: str) -> str:
        self.feed(html or "")
        return " ".join(self.parts)


class JobMatchingService:
    """
    Rule-based resume-to-job matching.

    Weighted score:
      - Technical skills: 35%
      - Role relevance: 30%
      - Experience relevance: 20%
      - Responsibilities: 15%

    A job is considered a match when:
      - The weighted score is at least 70%.
      - At least two required technical skills match.
      - The candidate's role is compatible with the job role.
    """

    MIN_MATCH_SCORE = 70.0
    MIN_MATCHED_SKILLS = 2

    WEIGHTS = {
        "skills": 35,
        "role": 30,
        "experience": 20,
        "responsibilities": 15,
    }

    SKILL_ALIASES = {
        "react": ["react", "react.js", "reactjs"],
        "react native": ["react native", "react-native"],
        "javascript": ["javascript", "js", "ecmascript"],
        "typescript": ["typescript", "ts"],
        "html": ["html", "html5"],
        "css": ["css", "css3"],
        "material ui": ["material ui", "mui"],
        "redux": ["redux", "redux toolkit"],
        "mobx": ["mobx"],
        "rest api": ["rest api", "rest apis", "restful api", "restful apis", "restful services"],
        "graphql": ["graphql"],
        "apollo": ["apollo", "apollo client"],
        "vite": ["vite"],
        "node.js": ["node.js", "nodejs", "node"],
        "python": ["python"],
        "fastapi": ["fastapi"],
        "postgresql": ["postgresql", "postgres"],
        "sql": ["sql"],
        "git": ["git", "github", "gitlab"],
        "ci/cd": ["ci/cd", "continuous integration", "continuous deployment"],
        "next.js": ["next.js", "nextjs"],
        "angular": ["angular"],
        "vue": ["vue", "vue.js"],
        "java": ["java"],
        "spring boot": ["spring boot"],
        "c#": ["c#", "c sharp"],
        ".net": [".net", "dotnet"],
        "aws": ["aws", "amazon web services"],
        "azure": ["azure", "microsoft azure"],
        "docker": ["docker"],
        "kubernetes": ["kubernetes", "k8s"],
        "mongodb": ["mongodb", "mongo db"],
        "mysql": ["mysql"],
        "firebase": ["firebase"],
        "tailwind css": ["tailwind css", "tailwind"],
        "sass": ["sass", "scss"],
        "jest": ["jest"],
        "cypress": ["cypress"],
        "playwright": ["playwright"],
        "excel": ["excel", "microsoft excel"],
        "figma": ["figma"],
    }

    ROLE_FAMILIES = {
        "frontend": [
            "frontend developer",
            "front end developer",
            "frontend engineer",
            "front end engineer",
            "react developer",
            "react engineer",
            "javascript developer",
            "typescript developer",
            "ui developer",
            "ui engineer",
        ],
        "mobile": [
            "mobile developer",
            "mobile engineer",
            "react native developer",
            "android developer",
            "ios developer",
        ],
        "backend": [
            "backend developer",
            "back end developer",
            "backend engineer",
            "python developer",
            "java developer",
            "fastapi developer",
            "node.js developer",
        ],
        "fullstack": [
            "full stack developer",
            "full-stack developer",
            "fullstack developer",
            "full stack engineer",
        ],
        "sales": [
            "account executive",
            "sales executive",
            "sales manager",
            "sales representative",
            "business development",
            "account manager",
        ],
        "design": [
            "ui designer",
            "ux designer",
            "product designer",
            "visual designer",
        ],
        "data": [
            "data analyst",
            "data engineer",
            "data scientist",
        ],
        "devops": [
            "devops engineer",
            "site reliability engineer",
            "platform engineer",
        ],
    }

    RELATED_ROLES = {
        "frontend": {"fullstack": 85, "mobile": 75},
        "mobile": {"frontend": 75, "fullstack": 75},
        "backend": {"fullstack": 85},
        "fullstack": {
            "frontend": 85,
            "backend": 85,
            "mobile": 75,
        },
    }

    RESPONSIBILITY_CATEGORIES = {
        "frontend_development": [
            "frontend",
            "front-end",
            "user interface",
            "ui development",
            "responsive interface",
            "web application",
            "component architecture",
        ],
        "mobile_development": [
            "mobile application",
            "mobile app",
            "react native",
            "android",
            "ios",
            "cross-platform",
        ],
        "api_integration": [
            "api integration",
            "rest api",
            "graphql",
            "integrate apis",
            "data handling",
        ],
        "testing": [
            "unit testing",
            "end-to-end testing",
            "playwright",
            "jest",
            "cypress",
            "automated testing",
        ],
        "performance": [
            "performance optimization",
            "load times",
            "application performance",
            "optimization",
        ],
        "collaboration": [
            "cross-functional teams",
            "collaborating with teams",
            "code reviews",
            "agile",
            "stakeholders",
        ],
        "sales": [
            "sales",
            "commercial negotiations",
            "contract renewals",
            "upsell",
            "pipeline generation",
            "client retention",
            "revenue growth",
            "customer acquisition",
        ],
        "account_management": [
            "account management",
            "client relationships",
            "customer relationships",
            "customer engagement",
        ],
        "project_management": [
            "project management",
            "manage projects",
            "project delivery",
            "project coordination",
        ],
    }

    @classmethod
    def normalize_text(cls, value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, (list, tuple, set)):
            value = " ".join(str(item) for item in value)

        return str(value).lower().strip()

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        pattern = (
            rf"(?<![a-z0-9+#])"
            rf"{re.escape(term.lower())}"
            rf"(?![a-z0-9+#])"
        )
        return re.search(pattern, text) is not None

    @classmethod
    def _extract_skills_from_text(cls, text: str) -> set[str]:
        normalized_text = cls.normalize_text(text)
        found_skills = set()

        for canonical_skill, aliases in cls.SKILL_ALIASES.items():
            if any(
                cls._contains_term(normalized_text, alias)
                for alias in aliases
            ):
                found_skills.add(canonical_skill)

        return found_skills

    @classmethod
    def _extract_candidate_skills(cls, profile: dict) -> set[str]:
        raw_skills = profile.get("technical_skills", [])

        if isinstance(raw_skills, str):
            raw_skills = [raw_skills]

        candidate_skills = set()

        for skill in raw_skills:
            candidate_skills.update(
                cls._extract_skills_from_text(skill)
            )

        return candidate_skills

    @staticmethod
    def _get_description_text(job: Any) -> str:
        description = getattr(job, "description", "") or ""

        parser = HTMLTextExtractor()
        parser.feed(unescape(description))

        return " ".join(parser.parts).lower()

    @staticmethod
    def _find_section(text: str, heading: str) -> str:
        """
        Find text after a heading until the next known section heading.
        Works with plain text extracted from HTML.
        """
        headings = [
            "minimum requirements",
            "preferred qualifications",
            "preferred requirements",
            "what you’ll do",
            "what you'll do",
            "responsibilities",
            "qualifications",
            "requirements",
            "who you are",
            "about the team",
        ]

        heading = heading.lower()
        start = text.find(heading)

        if start == -1:
            return ""

        section = text[start + len(heading):]
        next_positions = []

        for item in headings:
            position = section.find(item)

            if position >= 0:
                next_positions.append(position)

        if next_positions:
            section = section[:min(next_positions)]

        return section

    @classmethod
    def _extract_job_skill_groups(cls, job: Any) -> tuple[set, set]:
        description = cls._get_description_text(job)
        title = getattr(job, "title", "") or ""

        preferred_text = (
            cls._find_section(description, "preferred qualifications")
            or cls._find_section(description, "preferred requirements")
        )

        minimum_text = (
            cls._find_section(description, "minimum requirements")
            or cls._find_section(description, "requirements")
        )

        structured_skills = getattr(job, "required_skills", None) or []

        if isinstance(structured_skills, str):
            structured_skills = [structured_skills]

        required_skills = set()

        for skill in structured_skills:
            required_skills.update(
                cls._extract_skills_from_text(skill)
            )

        if not required_skills:
            required_skills = cls._extract_skills_from_text(
                f"{title} {minimum_text} {description}"
            )

        preferred_skills = cls._extract_skills_from_text(
            preferred_text
        )

        # A preferred skill should not also be counted as required.
        required_skills -= preferred_skills

        return required_skills, preferred_skills

    @classmethod
    def _classify_role(cls, text: str) -> str:
        normalized = cls.normalize_text(text)

        for family, titles in cls.ROLE_FAMILIES.items():
            for title in titles:
                if cls._contains_term(normalized, title):
                    return family

        # Additional frontend title patterns.
        if any(
            cls._contains_term(normalized, term)
            for term in ["frontend", "front-end"]
        ):
            return "frontend"

        if any(
            cls._contains_term(normalized, term)
            for term in ["backend", "back-end"]
        ):
            return "backend"

        return "other"

    @classmethod
    def _candidate_role_text(cls, profile: dict) -> str:
        parts = [
            profile.get("professional_title", ""),
            profile.get("professional_summary", ""),
        ]

        for experience in profile.get("work_experience", []) or []:
            parts.append(experience.get("designation", ""))
            parts.append(experience.get("company", ""))

        return " ".join(str(part) for part in parts if part)

    @classmethod
    def _calculate_role_score(
        cls,
        candidate_role: str,
        job_role: str,
    ) -> float:
        if candidate_role == "other" or job_role == "other":
            return 0.0

        if candidate_role == job_role:
            return 100.0

        related_score = cls.RELATED_ROLES.get(
            candidate_role, {}
        ).get(job_role)

        return float(related_score or 0.0)

    @classmethod
    def _extract_required_experience(cls, text: str) -> float | None:
        normalized = cls.normalize_text(text)

        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)",
            r"(\d+(?:\.\d+)?)\s*\+\s*years?",
            r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s*\+",
            r"minimum\s+of\s+(\d+(?:\.\d+)?)\s+years?",
            r"at\s+least\s+(\d+(?:\.\d+)?)\s+years?",
            r"(\d+(?:\.\d+)?)\s+years?\s+of\s+experience",
            r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)[’']?\s*(?:experience|professional experience)",
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized)

            if match:
                return float(match.group(1))

        return None

    @classmethod
    def _calculate_experience_score(
        cls,
        candidate_years: Any,
        required_years: float | None,
    ) -> float:
        if required_years is None:
            return 100.0

        try:
            candidate_years = float(candidate_years or 0)
        except (TypeError, ValueError):
            candidate_years = 0.0

        if candidate_years >= required_years:
            return 100.0

        if required_years <= 0:
            return 100.0

        return round(
            min(candidate_years / required_years * 100, 100),
            2,
        )

    @classmethod
    def _extract_responsibility_categories(
        cls,
        text: str,
    ) -> set[str]:
        normalized = cls.normalize_text(text)
        categories = set()

        for category, terms in cls.RESPONSIBILITY_CATEGORIES.items():
            if any(
                cls._contains_term(normalized, term)
                for term in terms
            ):
                categories.add(category)

        return categories

    @classmethod
    def _calculate_responsibility_score(
        cls,
        candidate_text: str,
        job_text: str,
    ) -> tuple[float, list[str]]:
        candidate_categories = (
            cls._extract_responsibility_categories(candidate_text)
        )
        job_categories = (
            cls._extract_responsibility_categories(job_text)
        )

        if not job_categories:
            return 0.0, []

        matched = sorted(candidate_categories & job_categories)

        score = round(
            len(matched) / len(job_categories) * 100,
            2,
        )

        return score, matched

    @classmethod
    def analyze(cls, profile: dict, job: Any) -> dict:
        candidate_skills = cls._extract_candidate_skills(profile)

        required_skills, preferred_skills = (
            cls._extract_job_skill_groups(job)
        )

        matched_skills = sorted(
            candidate_skills & required_skills
        )
        missing_skills = sorted(
            required_skills - candidate_skills
        )
        missing_preferred_skills = sorted(
            preferred_skills - candidate_skills
        )

        total_job_skills = len(required_skills)

        if total_job_skills:
            skill_score = round(
                len(matched_skills) / total_job_skills * 100,
                2,
            )
        else:
            # No detected required technical skills.
            skill_score = 0.0

        candidate_role_text = cls._candidate_role_text(profile)
        candidate_role = cls._classify_role(candidate_role_text)

        job_title = getattr(job, "title", "") or ""
        job_role = cls._classify_role(job_title)

        role_score = cls._calculate_role_score(
            candidate_role,
            job_role,
        )

        description_text = cls._get_description_text(job)

        minimum_section = (
            cls._find_section(
                description_text,
                "minimum requirements",
            )
            or cls._find_section(
                description_text,
                "requirements",
            )
        )

        required_experience = cls._extract_required_experience(
            minimum_section or description_text
        )
        if required_experience is None:
            required_experience = cls._extract_required_experience(description_text)
        if required_experience is None:
            required_experience = getattr(job, "experience_min", None)

        experience_score = cls._calculate_experience_score(
            profile.get("total_experience_years", 0),
            required_experience,
        )

        candidate_responsibilities = []

        for experience in profile.get("work_experience", []) or []:
            candidate_responsibilities.extend(
                experience.get("responsibilities", []) or []
            )

        for project in profile.get("projects", []) or []:
            candidate_responsibilities.append(
                project.get("description", "")
            )

        candidate_responsibility_text = " ".join(
            str(item) for item in candidate_responsibilities
        )

        responsibility_score, matched_responsibility_categories = (
            cls._calculate_responsibility_score(
                candidate_responsibility_text,
                description_text,
            )
        )

        weighted_score = (
            skill_score * cls.WEIGHTS["skills"] / 100
            + role_score * cls.WEIGHTS["role"] / 100
            + experience_score * cls.WEIGHTS["experience"] / 100
            + responsibility_score
            * cls.WEIGHTS["responsibilities"]
            / 100
        )

        match_score = round(weighted_score, 2)

        rejection_reasons = []

        if candidate_role != job_role:
            rejection_reasons.append("role_mismatch")

        if (
            required_experience is not None
            and float(profile.get("total_experience_years") or 0)
            < required_experience
        ):
            rejection_reasons.append("insufficient_experience")

        if len(matched_skills) < cls.MIN_MATCHED_SKILLS:
            rejection_reasons.append("insufficient_skill_match")

        if match_score < cls.MIN_MATCH_SCORE:
            rejection_reasons.append("low_match_score")

        # A known, incompatible role must never pass based on
        # coincidental skill overlap.
        role_compatible = (
            candidate_role == job_role
            or role_score > 0
        )

        is_match = (
            match_score >= cls.MIN_MATCH_SCORE
            and len(matched_skills) >= cls.MIN_MATCHED_SKILLS
            and role_compatible
        )

        decision = "matched" if is_match else "not_matched"

        return {
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "candidate_skills": sorted(candidate_skills),
            "job_skills": sorted(required_skills),
            "matched_skill_count": len(matched_skills),
            "total_job_skills": total_job_skills,
            "decision": decision,

            "role_family": job_role,
            "candidate_role_family": candidate_role,
            "role_match_score": role_score,
            "skill_match_score": skill_score,
            "experience_match_score": experience_score,
            "responsibility_match_score": responsibility_score,

            "required_skills": sorted(required_skills),
            "preferred_skills": sorted(preferred_skills),
            "missing_preferred_skills": missing_preferred_skills,

            "required_experience_years": required_experience,
            "candidate_experience_years": float(
                profile.get("total_experience_years") or 0
            ),

            "matched_responsibility_categories": (
                matched_responsibility_categories
            ),
            "rejection_reasons": rejection_reasons,

            "match_explanation": (
                f"Candidate role: {candidate_role}. "
                f"Job role: {job_role}. "
                f"Weighted match score: {match_score}%."
            ),
        }
