"""
Job Radar — Main Orchestrator
Entry point: scrape all sources → filter → dedup → save to data/jobs.json
"""

import sys
import yaml
from scrapers.group_a_jobspy import JobSpyScraper
from scrapers.group_a_linkedin import LinkedInScraper
from scrapers.group_b_remoteok import RemoteOKScraper
from scrapers.group_b_himalayas import HimalayasScraper
from scrapers.group_b_jobicy import JobicyScraper
from scrapers.group_b_wellfound import WellfoundScraper
from scrapers.group_c_vietnamworks import VietnamWorksScraper
from scrapers.group_c_itviec import ITviecScraper
from scrapers.group_c_topcv import TopCVScraper
from scrapers.group_c_turing import TuringScraper
from scrapers.group_d_weworkremotely import WeWorkRemotelyScraper
from processor.filter import apply_filters
from processor.dedup import load_existing_jobs, find_new_jobs, merge_and_save
from enricher.gemini import enrich_jobs_batch


def load_config() -> dict:
    with open("config/keywords.yml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    keywords = config.get("search_keywords", [])

    print(f"[main] Starting scrape for {len(keywords)} keywords across 11 sources")
    print(f"[main] Keywords: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

    all_scraped = []

    scrapers = [
        # Group A: JobSpy-based (global, 30 days)
        LinkedInScraper(),
        JobSpyScraper(),
        # Group B: API-based (remote jobs)
        RemoteOKScraper(),
        HimalayasScraper(),
        JobicyScraper(),
        WellfoundScraper(),  # Playwright - may fail on CI
        # Group C: Vietnamese job sites
        VietnamWorksScraper(),
        ITviecScraper(),
        TopCVScraper(),
        TuringScraper(),  # Playwright - may fail on CI
        # Group D: New sources
        WeWorkRemotelyScraper(),
    ]

    for scraper in scrapers:
        results = scraper.safe_scrape(keywords, max_results=100)
        all_scraped.extend(results)

    print(f"\n[main] Total scraped (before filter): {len(all_scraped)}")

    # Apply keyword + exclusion filters
    filtered = apply_filters(all_scraped, config)
    print(f"[main] After filter: {len(filtered)}")

    # Dedup against existing jobs.json
    existing = load_existing_jobs()
    new_jobs = find_new_jobs(filtered, existing)
    print(f"[main] New jobs (not seen before): {len(new_jobs)}")

    if new_jobs:
        # Optional: enrich with Gemini (silently skips if no API key)
        new_jobs = enrich_jobs_batch(new_jobs)

        count = merge_and_save(new_jobs, existing)
        print(f"\n[main] ✅ Saved {count} new jobs to data/jobs.json")
        print(f"[main] Total jobs in database: {count + len(existing)}")
    else:
        print("\n[main] No new jobs found. Skipping commit.")
        sys.exit(1)  # Signal no change to GitHub Actions


if __name__ == "__main__":
    main()
