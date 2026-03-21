"""
JobSpy scraper — covers LinkedIn, Indeed, Google Jobs concurrently.
Uses python-jobspy library.
"""

import time
import random
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id
from datetime import datetime

try:
    from jobspy import scrape_jobs
    import pandas as pd
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


TECH_KEYWORDS = [
    "python", "sql", "spark", "pyspark", "dbt", "airflow", "docker",
    "kafka", "azure", "aws", "gcp", "power bi", "tableau", "mlflow",
    "data engineering", "analytics engineering", "machine learning",
    "deep learning", "pytorch", "tensorflow", "scikit-learn",
    "pandas", "numpy", "postgres", "bigquery", "snowflake", "databricks",
    "microsoft fabric", "synapse", "data warehouse", "medallion",
    "kubernetes", "ci/cd", "java", "scala", "golang", "rust",
    "react", "node.js", "typescript", "javascript",
]


class JobSpyScraper(BaseJobScraper):
    source_name = "jobspy_multi"

    def scrape(self, keywords: list[str], max_results: int = 25) -> list[Job]:
        if not JOBSPY_AVAILABLE:
            print("[jobspy] python-jobspy not installed — skipping")
            return []

        all_jobs = []

        for keyword in keywords:
            time.sleep(random.uniform(3, 7))
            try:
                # Scrape Vietnam-based jobs
                df = scrape_jobs(
                    site_name=["linkedin", "indeed", "google"],
                    search_term=keyword,
                    location="Vietnam",
                    results_wanted=max_results,
                    hours_old=24,
                    description_format="markdown",
                    country_indeed="vietnam",
                )
                all_jobs.extend(self._df_to_jobs(df))
            except Exception as e:
                print(f"[jobspy] keyword={keyword} (Vietnam) failed: {e}")

            time.sleep(random.uniform(2, 4))
            try:
                # Scrape remote international
                df_remote = scrape_jobs(
                    site_name=["linkedin", "indeed"],
                    search_term=keyword,
                    location="Remote",
                    is_remote=True,
                    results_wanted=max_results,
                    hours_old=24,
                    description_format="markdown",
                )
                all_jobs.extend(self._df_to_jobs(df_remote))
            except Exception as e:
                print(f"[jobspy] keyword={keyword} (Remote) failed: {e}")

        return all_jobs

    def _df_to_jobs(self, df) -> list[Job]:
        if df is None or df.empty:
            return []

        jobs = []
        for _, row in df.iterrows():
            url = str(row.get("job_url", "") or "")
            if not url:
                continue
            source = str(row.get("site", "indeed")).lower()
            if source not in ("linkedin", "indeed", "google"):
                source = "indeed"

            salary = self._parse_salary(row)

            jobs.append(Job(
                id=generate_job_id(source, url),
                source=source,
                url=url,
                title=str(row.get("title", "") or "").strip(),
                company=str(row.get("company", "N/A") or "N/A"),
                location=str(row.get("location", "N/A") or "N/A"),
                is_remote=bool(row.get("is_remote", False)),
                salary=salary,
                job_type=str(row.get("job_type", "N/A") or "N/A").lower(),
                tags=self._extract_tags(str(row.get("description", "") or "")),
                description_snippet=str(row.get("description", "") or "")[:300],
                posted_date=str(row.get("date_posted", "") or "")[:10],
                scraped_at=datetime.now().isoformat(),
                first_seen=datetime.now().isoformat(),
            ))
        return jobs

    def _parse_salary(self, row) -> str:
        try:
            import pandas as pd
            min_s = row.get("min_amount")
            max_s = row.get("max_amount")
            cur = row.get("currency", "USD") or "USD"
            interval = row.get("interval", "year") or "year"
            if pd.notna(min_s) and pd.notna(max_s):
                return f"{cur} {int(min_s):,} – {int(max_s):,}/{interval}"
        except Exception:
            pass
        return "N/A"

    def _extract_tags(self, description: str) -> list[str]:
        desc_lower = description.lower()
        return [kw for kw in TECH_KEYWORDS if kw in desc_lower]
