
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v1"

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

EMAIL = "bmk@gmail.com"
PASSWORD = "Murali@2001"

# Replace these with actual public job board identifiers.
GREENHOUSE_COMPANY = {
    "name": "Stripe",
    "source_type": "greenhouse",
    "source_url": "https://boards.greenhouse.io/stripe",
    "external_source_id": "stripe",
}

LEVER_COMPANY = {
    "name": "Palantir",
    "source_type": "lever",
    "source_url": "https://jobs.lever.co/palantir",
    "external_source_id": "palantir",
}


# --------------------------------------------------
# HTTP SESSION
# --------------------------------------------------

session = requests.Session()


def print_response(title, response):

    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    print("Status:", response.status_code)

    try:
        print(json.dumps(response.json(), indent=4))
    except ValueError:
        print(response.text)


# --------------------------------------------------
# 1. LOGIN
# --------------------------------------------------


def login():

    print("\n[1] Testing Login API")

    url = f"{BASE_URL}/auth/login"

    # Your FastAPI endpoint expects JSON.
    payload = {
        "email": EMAIL,
        "password": PASSWORD,
    }

    response = session.post(
        url,
        json=payload,
    )

    print_response("LOGIN RESPONSE", response)

    response.raise_for_status()

    token_data = response.json()

    access_token = token_data.get("access_token")

    if not access_token:
        raise RuntimeError(
            "Access token missing in login response"
        )

    session.headers.update({
        "Authorization": f"Bearer {access_token}"
    })

    print("\nLogin successful!")

    return access_token


# --------------------------------------------------
# 2. TEST AUTHENTICATED USER
# --------------------------------------------------

def test_current_user():

    print("\n[2] Testing Current User API")

    url = f"{BASE_URL}/auth/me"

    response = session.get(url)

    print_response("CURRENT USER RESPONSE", response)

    response.raise_for_status()


# --------------------------------------------------
# 3. CREATE JOB SOURCE
# --------------------------------------------------

def create_job_source(source_data):

    print(
        f"\n[3] Creating source: {source_data['name']}"
    )

    url = f"{BASE_URL}/job-sources"

    response = session.post(
        url,
        json=source_data,
    )

    print_response("CREATE SOURCE RESPONSE", response)

    response.raise_for_status()

    source = response.json()

    source_id = source.get("id")

    if not source_id:
        raise RuntimeError("Source ID missing in response")

    return source_id


# --------------------------------------------------
# 4. COLLECT JOBS
# --------------------------------------------------

def collect_jobs(source_id, source_name):

    print(
        f"\n[4] Collecting jobs from {source_name}"
    )

    url = (
        f"{BASE_URL}/job-sources/"
        f"{source_id}/collect"
    )

    response = session.post(url)

    print_response(
        f"{source_name} COLLECTION RESPONSE",
        response,
    )

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 5. GET ALL JOBS
# --------------------------------------------------

def get_all_jobs():

    print("\n[5] Testing Get All Jobs API")

    url = f"{BASE_URL}/jobs"

    response = session.get(url)

    print_response("ALL JOBS RESPONSE", response)

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 6. SEARCH JOBS
# --------------------------------------------------

def search_jobs(keyword):

    print(f"\n[6] Searching jobs: {keyword}")

    url = f"{BASE_URL}/jobs"

    params = {
        "search": keyword,
        "page": 1,
        "page_size": 10,
    }

    response = session.get(
        url,
        params=params,
    )

    print_response("SEARCH JOBS RESPONSE", response)

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# MAIN TEST FLOW
# --------------------------------------------------

def main():

    try:

        # Login
        login()

        # Verify authentication
        test_current_user()

        # Register Greenhouse source
        greenhouse_id = create_job_source(
            GREENHOUSE_COMPANY
        )

        # Register Lever source
        lever_id = create_job_source(
            LEVER_COMPANY
        )

        # Collect Greenhouse jobs
        collect_jobs(
            greenhouse_id,
            "Greenhouse",
        )

        # Collect Lever jobs
        collect_jobs(
            lever_id,
            "Lever",
        )

        # Get all collected jobs
        get_all_jobs()

        # Search jobs
        search_jobs("Frontend Developer")

        print("\n" + "=" * 60)
        print("ALL API TESTS COMPLETED")
        print("=" * 60)

    except requests.exceptions.HTTPError as error:

        print("\nHTTP ERROR:", error)

        if error.response is not None:
            print(error.response.text)

        sys.exit(1)

    except requests.exceptions.RequestException as error:

        print("\nREQUEST ERROR:", error)
        sys.exit(1)

    except Exception as error:

        print("\nTEST FAILED:", error)
        sys.exit(1)


if __name__ == "__main__":
    main()
