"""
Keyword + tag matching filters applied after scraping.
"""

from processor.normalizer import Job


def apply_filters(jobs: list[Job], config: dict) -> list[Job]:
    """Apply keyword and exclusion filters from config/keywords.yml."""
    title_excludes = [x.lower() for x in config.get("title_exclude", [])]
    locations_include = [x.lower() for x in config.get("locations_include", [])]
    min_salary = config.get("min_salary_usd", 0)

    filtered = []
    for job in jobs:
        # Exclude jobs with blocked title words
        if title_excludes:
            title_lower = job.title.lower()
            if any(ex in title_lower for ex in title_excludes):
                continue

        # Location filter (if locations_include is non-empty)
        if locations_include:
            loc_lower = job.location.lower()
            if not any(loc in loc_lower for loc in locations_include):
                # Also allow remote jobs through
                if not job.is_remote:
                    continue

        filtered.append(job)

    return filtered
