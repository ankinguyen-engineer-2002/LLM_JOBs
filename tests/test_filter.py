"""Tests for processor/filter.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from processor.normalizer import Job
from processor.filter import apply_filters


def make_job(title="Data Engineer", location="Ho Chi Minh", is_remote=False, tags=None) -> Job:
    return Job(
        id="test123",
        source="test",
        url="https://example.com/job",
        title=title,
        company="TestCo",
        location=location,
        is_remote=is_remote,
        tags=tags or [],
    )


class TestApplyFilters:
    def test_no_filters(self):
        """Returns all jobs when no filters active."""
        config = {"title_exclude": [], "locations_include": []}
        jobs = [make_job(), make_job(title="ML Engineer")]
        result = apply_filters(jobs, config)
        assert len(result) == 2

    def test_title_exclude(self):
        """Excludes jobs matching title_exclude."""
        config = {"title_exclude": ["intern", "student"], "locations_include": []}
        jobs = [
            make_job(title="Data Engineer"),
            make_job(title="Data Engineer Intern"),
            make_job(title="Student Developer"),
        ]
        result = apply_filters(jobs, config)
        assert len(result) == 1
        assert result[0].title == "Data Engineer"

    def test_title_exclude_case_insensitive(self):
        """Title exclusion is case-insensitive."""
        config = {"title_exclude": ["INTERN"], "locations_include": []}
        jobs = [make_job(title="Software intern")]
        result = apply_filters(jobs, config)
        assert len(result) == 0

    def test_location_include_filters(self):
        """Only keeps jobs from specified locations."""
        config = {"title_exclude": [], "locations_include": ["Ho Chi Minh", "Remote"]}
        jobs = [
            make_job(location="Ho Chi Minh City"),
            make_job(location="Hanoi"),
            make_job(location="Remote", is_remote=True),
        ]
        result = apply_filters(jobs, config)
        assert len(result) == 2

    def test_remote_jobs_pass_location_filter(self):
        """Remote jobs always pass location filter."""
        config = {"title_exclude": [], "locations_include": ["Ho Chi Minh"]}
        jobs = [make_job(location="New York", is_remote=True)]
        result = apply_filters(jobs, config)
        assert len(result) == 1

    def test_empty_locations_include_allows_all(self):
        """Empty locations_include means no location filter."""
        config = {"title_exclude": [], "locations_include": []}
        jobs = [make_job(location="New York"), make_job(location="Tokyo")]
        result = apply_filters(jobs, config)
        assert len(result) == 2

    def test_combined_filters(self):
        """Title exclude + location include work together."""
        config = {
            "title_exclude": ["intern"],
            "locations_include": ["Vietnam"],
        }
        jobs = [
            make_job(title="Data Engineer", location="Vietnam"),
            make_job(title="Intern Data", location="Vietnam"),
            make_job(title="Data Engineer", location="USA"),
        ]
        result = apply_filters(jobs, config)
        assert len(result) == 1
        assert result[0].title == "Data Engineer"
        assert result[0].location == "Vietnam"
