"""
Unified Job Schema — all scrapers normalize output to this format.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import hashlib
import re


# Valid source names
SOURCE_NAMES = [
    "itviec", "vietnamworks", "topcv",
    "linkedin", "indeed", "google",
    "remoteok", "himalayas", "jobicy",
    "wellfound", "turing",
]


@dataclass
class Job:
    # === IDENTITY (required) ===
    id: str                          # sha256(source + url)[:16]
    source: str                      # One of SOURCE_NAMES
    url: str                         # Direct link to posting

    # === CONTENT (required) ===
    title: str                       # Job title
    company: str                     # Company name

    # === CONTENT (optional) ===
    location: str = "N/A"
    is_remote: bool = False
    salary: str = "N/A"
    job_type: str = "N/A"            # full_time | part_time | contract | internship | N/A
    tags: list[str] = field(default_factory=list)
    description_snippet: str = ""    # First 300 chars, HTML stripped

    # === TIMESTAMPS ===
    posted_date: str = ""            # ISO date "2026-03-22"
    scraped_at: str = ""             # ISO datetime
    first_seen: str = ""             # Set once, never overwritten


def generate_job_id(source: str, url: str) -> str:
    """Stable ID: does not change across runs for the same job."""
    raw = f"{source}::{url.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def validate_job(job: Job) -> bool:
    """Check if a job has all required fields."""
    return bool(job.id and job.source and job.url and job.title and job.company)
