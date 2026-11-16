import re


MAX_SEARCH_QUERIES = 6

ROLE_ALIASES = (
    (r"\bfront[\s-]?end\b", ("Frontend Engineer", "Web Developer", "UI Developer")),
    (r"\bback[\s-]?end\b", ("Backend Engineer", "Backend Developer")),
    (r"\bfull[\s-]?stack\b", ("Full Stack Engineer", "Full Stack Developer")),
    (r"\bsoftware (?:developer|engineer)\b", ("Software Engineer", "Software Developer")),
)

SKILL_QUERIES = (
    ({"react native"}, "React Native Developer"),
    ({"react", "react.js", "reactjs", "next.js", "nextjs"}, "React Developer"),
    ({"angular", "angularjs"}, "Angular Developer"),
    ({"vue", "vue.js", "vuejs"}, "Vue Developer"),
    ({"typescript", "javascript"}, "JavaScript Developer"),
    ({"node.js", "nodejs", "express.js"}, "Node.js Developer"),
    ({"python", "django", "fastapi", "flask"}, "Python Developer"),
    ({"java", "spring boot"}, "Java Developer"),
    ({"c#", ".net", "asp.net"}, ".NET Developer"),
)


def resume_search_queries(profile: dict) -> list[str]:
    title = profile.get("professional_title") or ""
    skills = {skill.strip().casefold() for skill in profile.get("technical_skills") or []}
    previous_titles = [
        item.get("designation") for item in profile.get("work_experience") or []
    ]
    aliases = [
        alias for pattern, titles in ROLE_ALIASES
        if re.search(pattern, title, flags=re.IGNORECASE)
        for alias in titles
    ]
    skill_titles = [query for names, query in SKILL_QUERIES if names & skills]
    candidates = [title, *skill_titles[:2], *previous_titles[:1], *aliases, *skill_titles[2:], *previous_titles[1:]]

    queries = {}
    for candidate in candidates:
        if candidate:
            query = " ".join(candidate.split())[:100]
            if query:
                queries.setdefault(query.casefold(), query)
    return list(queries.values())[:MAX_SEARCH_QUERIES] or ["Software Developer"]
