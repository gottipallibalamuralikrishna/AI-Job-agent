
from types import SimpleNamespace

from app.collectors.rss import RSSCollector


source = SimpleNamespace(
    name="Hacker News",
    source_url="https://hnrss.org/jobs",
    external_source_id="hn-jobs",
)

collector = RSSCollector()

try:
    jobs = collector.fetch_jobs(source)

    print(f"\nTotal jobs fetched: {len(jobs)}")

    for job in jobs[:5]:
        print("\n-----------------------------")
        print("Title:", job["title"])
        print("Company:", job["company_name"])
        print("Location:", job["location"])
        print("Application URL:", job["application_url"])
        print("Posted At:", job["posted_at"])

finally:
    collector.close()
