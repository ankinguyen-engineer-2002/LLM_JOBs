"""Tests for processor/dedup.py"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from processor.normalizer import Job
from processor.dedup import find_new_jobs, merge_and_save, load_existing_jobs


def make_job(id: str, source: str = "test", first_seen: str = "2026-01-01") -> Job:
    return Job(
        id=id,
        source=source,
        url=f"https://example.com/{id}",
        title=f"Job {id}",
        company="TestCo",
        scraped_at="2026-03-22T00:00:00",
        first_seen=first_seen,
    )


class TestFindNewJobs:
    def test_all_new(self):
        """All jobs are new when existing is empty."""
        jobs = [make_job("a"), make_job("b")]
        existing = {}
        new = find_new_jobs(jobs, existing)
        assert len(new) == 2

    def test_all_existing(self):
        """No new jobs when all already exist."""
        jobs = [make_job("a"), make_job("b")]
        existing = {"a": {"id": "a"}, "b": {"id": "b"}}
        new = find_new_jobs(jobs, existing)
        assert len(new) == 0

    def test_mixed(self):
        """Only truly new jobs are returned."""
        jobs = [make_job("a"), make_job("b"), make_job("c")]
        existing = {"a": {"id": "a"}}
        new = find_new_jobs(jobs, existing)
        assert len(new) == 2
        assert {j.id for j in new} == {"b", "c"}


class TestMergeAndSave:
    def test_writes_valid_json(self, tmp_path):
        """merge_and_save creates valid JSON file."""
        jobs_file = tmp_path / "data" / "jobs.json"
        with patch("processor.dedup.JOBS_FILE", jobs_file):
            new_jobs = [make_job("a"), make_job("b")]
            count = merge_and_save(new_jobs, {})
            assert count == 2
            assert jobs_file.exists()
            data = json.loads(jobs_file.read_text())
            assert len(data) == 2

    def test_merges_with_existing(self, tmp_path):
        """New jobs are merged with existing ones."""
        jobs_file = tmp_path / "data" / "jobs.json"
        existing = {
            "existing1": {
                "id": "existing1", "source": "test", "url": "u",
                "title": "t", "company": "c",
                "scraped_at": "2026-03-21T00:00:00",
                "first_seen": "2026-01-01",
            }
        }
        with patch("processor.dedup.JOBS_FILE", jobs_file):
            new_jobs = [make_job("new1")]
            merge_and_save(new_jobs, existing)
            data = json.loads(jobs_file.read_text())
            assert len(data) == 2

    def test_preserves_first_seen(self, tmp_path):
        """Existing job's first_seen is not overwritten."""
        jobs_file = tmp_path / "data" / "jobs.json"
        existing = {
            "a": {
                "id": "a", "source": "test", "url": "u",
                "title": "t", "company": "c",
                "scraped_at": "2026-03-21T00:00:00",
                "first_seen": "2025-12-01",
            }
        }
        with patch("processor.dedup.JOBS_FILE", jobs_file):
            merge_and_save([], existing)
            data = json.loads(jobs_file.read_text())
            assert data[0]["first_seen"] == "2025-12-01"

    def test_sorted_by_scraped_at(self, tmp_path):
        """Output is sorted by scraped_at descending."""
        jobs_file = tmp_path / "data" / "jobs.json"
        with patch("processor.dedup.JOBS_FILE", jobs_file):
            j1 = make_job("old")
            j1.scraped_at = "2026-01-01T00:00:00"
            j2 = make_job("new")
            j2.scraped_at = "2026-03-22T00:00:00"
            merge_and_save([j1, j2], {})
            data = json.loads(jobs_file.read_text())
            assert data[0]["id"] == "new"
            assert data[1]["id"] == "old"
