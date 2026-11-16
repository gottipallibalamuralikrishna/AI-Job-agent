"""Country filtering and explicit eligibility for international remote work."""
import re
from html import unescape

INDIA_LOCATIONS = (
    "india", "bengaluru", "bangalore", "hyderabad", "chennai", "mumbai", "pune",
    "delhi", "noida", "gurgaon", "gurugram", "kolkata", "ahmedabad", "chandigarh",
    "mohali", "kochi", "cochin", "thiruvananthapuram", "trivandrum", "coimbatore",
    "indore", "jaipur", "bhubaneswar", "nagpur", "mysore", "mysuru", "visakhapatnam",
    "vijayawada", "mangalore", "mangaluru", "kerala", "telangana", "karnataka",
)


def matches_country(location, country):
    if not country:
        return True
    value = str(location or "").lower()
    terms = INDIA_LOCATIONS if country.lower() == "india" else (country.lower(),)
    return any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", value) for term in terms)


def _get(job, field, default=None):
    return job.get(field, default) if isinstance(job, dict) else getattr(job, field, default)


def _plain(value):
    text = unescape(str(value or ""))
    text = re.sub(r"<(?:script|style)\b[^>]*>[\s\S]*?</(?:script|style)>", " ", text, flags=re.I)
    return re.sub(r"<[^>]+>", "\n", text).lower()


def infer_work_mode(job):
    mode = _get(job, "work_mode")
    title_location = _plain(f"{_get(job, 'title', '')} {_get(job, 'location', '')}")
    description = _plain(_get(job, "description", ""))
    if re.search(r"\b(?:not (?:a )?remote(?: role| position| job)?|no remote (?:option|work)|remote (?:work )?(?:is )?not (?:available|offered|allowed))\b", title_location + " " + description):
        return "onsite"
    if mode in {"remote", "hybrid", "onsite"}:
        return mode
    if re.search(r"\bhybrid\b", title_location):
        return "hybrid"
    if re.search(r"\b(?:on[ -]?site|in[ -]office)\b", title_location):
        return "onsite"
    if re.search(r"\b(?:not remote|no remote|remote (?:work )?(?:is )?not (?:available|offered|allowed))\b", description):
        return "onsite"
    location = _plain(_get(job, "location", ""))
    if re.search(r"\b(?:remote|work from home|work from anywhere|home[ -]based)\b", location):
        return "remote"
    if re.search(r"(?:\(|\[| - |, )\s*(?:fully )?remote\b", _plain(_get(job, "title", ""))):
        return "remote"
    if re.search(r"\b(?:fully remote|100% remote|remote[- ]first (?:role|position|job)|"
                 r"(?:role|position|job) (?:is |will be )?(?:fully )?remote|"
                 r"work (?:remotely|from anywhere|from home))\b", description):
        return "remote"
    return None


def applicant_locations(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return list(dict.fromkeys(name for item in value for name in applicant_locations(item)))
    if isinstance(value, dict):
        return applicant_locations(value.get("name") or value.get("addressCountry") or value.get("address"))
    return []


_GLOBAL = r"(?:worldwide|anywhere in the world|any country|all countries|work from anywhere)"
_FOREIGN = r"(?:united states|usa|u\.?s\.?|united kingdom|uk|canada|australia|europe|eu|eea|emea|north america|americas|singapore|germany|france|japan)"


def _country_named(text, country):
    # Eligibility lists contain country names, not arbitrary cities or mentions
    # of an employer's Indian office.
    if country.lower() == "india" and text.strip().upper() == "IN":
        return True
    return bool(re.search(r"\b" + re.escape(country.lower()) + r"\b", text.lower()))


def remote_open_to_country(job, country):
    if infer_work_mode(job) != "remote":
        return False
    location = _plain(_get(job, "location", ""))
    description = _plain(_get(job, "description", ""))
    # Keep abbreviations such as U.S. together while separating sentences.
    description = re.sub(r"\bu\.s\.(?:a\.)?", "united states", description)
    clauses = re.split(r"[\n;!]|\.(?:\s|$)", description)
    # Explicit residency/country restrictions override general remote language.
    for clause in [location, *clauses]:
        country_pattern = r"\b" + re.escape(country.lower()) + r"\b"
        if re.search(r"(?:excluding|except|outside|not (?:open|available) to|(?:cannot|can't|do not|don't) (?:hire|employ)(?: in| from)?)\s+" + country_pattern, clause):
            return False
        residency = re.search(r"\b(?:must (?:currently )?(?:be (?:based|located|resident)|reside|live)|"
                              r"(?:role|position|applicants|candidates|employees) (?:is |are |must be )?(?:based|located|resident))\s+(?:in|within)\b", clause)
        country_only = re.search(r"\b(?:only (?:open|available) (?:to|in)|only (?:within|in|from)|"
                                 r"(?:applicants|candidates) (?:from|in).{0,60}\bonly|"
                                 r"(?:role|position|hiring|applications|employment) (?:is |are )?(?:restricted|limited) to)\b", clause)
        if (residency or country_only) and not _country_named(clause, country):
            return False
        restricted = re.search(r"\b(?:only|must (?:be|reside|live)|required to (?:be|reside)|"
                               r"(?:based|located|resident|residing) (?:in|within)|restricted to|limited to)\b", clause)
        if restricted and re.search(r"\b" + _FOREIGN + r"\b", clause) and not _country_named(clause, country):
            return False
    eligible = _get(job, "remote_eligible_locations", []) or []
    if eligible:
        return any(_country_named(str(value), country) or matches_country(str(value), country)
                   or re.fullmatch(_GLOBAL, str(value).lower().strip())
                   for value in eligible)
    # "Remote - US" is a work-location restriction, not worldwide eligibility.
    if re.search(r"\b(?:remote|home[ -]based|work from home)\b", location) and not (matches_country(location, country) or re.search(_GLOBAL, location)):
        qualifier = re.sub(r"\b(?:fully|remote|home[ -]based|work from home|position|role)\b|[\s,()\[\]/-]", "", location)
        if qualifier:
            return False
    if re.search(_GLOBAL, location) or matches_country(location, country):
        return True
    for clause in clauses:
        explicit_country = re.search(r"\b(?:remote(?:ly)?\s+(?:from|in|within)|"
            r"(?:applicants|candidates|applications|employees)\b.{0,50}\b(?:from|in)|"
            r"(?:open|available)\s+to|(?:must be|be)\s+(?:based|located)\s+in)\b", clause)
        if explicit_country and _country_named(clause, country):
            return True
        if re.search(_GLOBAL, clause) and re.search(r"\b(?:work|role|position|job|applicants|candidates|applications|hire)\b", clause):
            return True
    return False


def matches_job_location(job, country, include_international_remote=False):
    if matches_country(_get(job, "location"), country):
        return not country or infer_work_mode(job) != "remote" or remote_open_to_country(job, country)
    return bool(include_international_remote and country and remote_open_to_country(job, country))
