"""
Deduplication engine — merge new scraped jobs with existing jobs.json.
"""

import json
from pathlib import Path
from processor.normalizer import Job, validate_job
from dataclasses import asdict

JOBS_FILE = Path("data/jobs.json")


def load_existing_jobs() -> dict[str, dict]:
    """Returns dict keyed by job ID."""
    if not JOBS_FILE.exists():
        return {}
    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {job["id"]: job for job in raw if "id" in job}
    except (json.JSONDecodeError, KeyError):
        return {}


def find_new_jobs(scraped_jobs: list[Job], existing: dict[str, dict]) -> list[Job]:
    """Return only jobs not present in existing dict."""
    new = []
    for job in scraped_jobs:
        if not validate_job(job):
            continue
        if job.id not in existing:
            new.append(job)
    return new


def merge_and_save(new_jobs: list[Job], existing: dict[str, dict]) -> int:
    """Merge new + existing, save to jobs.json. Return count of new jobs added."""
    new_dicts = [asdict(j) for j in new_jobs]
    all_jobs = new_dicts + list(existing.values())
    all_jobs.sort(key=lambda x: x.get("scraped_at", ""), reverse=True)

    JOBS_FILE.parent.mkdir(exist_ok=True)
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=2)

    return len(new_jobs)
