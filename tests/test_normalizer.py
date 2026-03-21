"""Tests for processor/normalizer.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from processor.normalizer import Job, generate_job_id, strip_html, validate_job


class TestGenerateJobId:
    def test_deterministic(self):
        """Same input always produces same output."""
        id1 = generate_job_id("linkedin", "https://example.com/job/123")
        id2 = generate_job_id("linkedin", "https://example.com/job/123")
        assert id1 == id2

    def test_different_inputs_different_ids(self):
        """Different inputs produce different IDs."""
        id1 = generate_job_id("linkedin", "https://example.com/job/123")
        id2 = generate_job_id("indeed", "https://example.com/job/123")
        id3 = generate_job_id("linkedin", "https://example.com/job/456")
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3

    def test_length(self):
        """ID is exactly 16 chars."""
        id1 = generate_job_id("remoteok", "https://remoteok.com/l/12345")
        assert len(id1) == 16

    def test_case_insensitive_url(self):
        """URL is lowercased before hashing."""
        id1 = generate_job_id("linkedin", "https://Example.COM/Job/123")
        id2 = generate_job_id("linkedin", "https://example.com/job/123")
        assert id1 == id2

    def test_strips_whitespace(self):
        """Trailing/leading whitespace doesn't affect ID."""
        id1 = generate_job_id("indeed", "  https://example.com/job  ")
        id2 = generate_job_id("indeed", "https://example.com/job")
        assert id1 == id2


class TestJob:
    def test_defaults(self):
        """Job initializes with correct defaults."""
        job = Job(
            id="abc123",
            source="linkedin",
            url="https://example.com",
            title="Data Engineer",
            company="Acme Corp",
        )
        assert job.location == "N/A"
        assert job.is_remote is False
        assert job.salary == "N/A"
        assert job.job_type == "N/A"
        assert job.tags == []
        assert job.description_snippet == ""
        assert job.posted_date == ""
        assert job.scraped_at == ""
        assert job.first_seen == ""

    def test_custom_values(self):
        """Job accepts custom values."""
        job = Job(
            id="abc123",
            source="remoteok",
            url="https://example.com",
            title="ML Engineer",
            company="StartupX",
            location="Remote",
            is_remote=True,
            salary="$5,000 – $8,000/month",
            tags=["python", "ml"],
        )
        assert job.is_remote is True
        assert job.salary == "$5,000 – $8,000/month"
        assert "python" in job.tags


class TestStripHtml:
    def test_strips_tags(self):
        assert strip_html("<p>Hello <b>world</b></p>") == "Hello world"

    def test_empty_string(self):
        assert strip_html("") == ""

    def test_no_html(self):
        assert strip_html("plain text") == "plain text"


class TestValidateJob:
    def test_valid_job(self):
        job = Job(id="a", source="b", url="c", title="d", company="e")
        assert validate_job(job) is True

    def test_missing_title(self):
        job = Job(id="a", source="b", url="c", title="", company="e")
        assert validate_job(job) is False

    def test_missing_id(self):
        job = Job(id="", source="b", url="c", title="d", company="e")
        assert validate_job(job) is False
