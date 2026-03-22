"""
LinkedIn scraper — global scope, 30-day window.
Uses python-jobspy. Scrapes all locations worldwide.
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
    "microsoft fabric", "synapse", "data warehouse",
    "kubernetes", "ci/cd", "java", "scala",
    "llm", "gpt", "langchain", "openai", "prompt engineering",
    "generative ai", "nlp", "huggingface", "fine-tuning",
]


class LinkedInScraper(BaseJobScraper):
    source_name = "linkedin"

    # Keyword batches to stay under timeout
    MAX_KEYWORDS = 6

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not JOBSPY_AVAILABLE:
            print("[linkedin] python-jobspy not installed — skipping")
            return []

        all_jobs = []
        seen_urls = set()

        limited_kws = keywords[:self.MAX_KEYWORDS]

        for keyword in limited_kws:
            # Global search (no location restriction)
            time.sleep(random.uniform(2, 4))
            try:
                df = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=keyword,
                    results_wanted=min(max_results, 25),
                    hours_old=720,  # 30 days
                    description_format="markdown",
                )
                all_jobs.extend(self._df_to_jobs(df, seen_urls))
                print(f"[linkedin] global '{keyword}': {len(df) if df is not None else 0} results")
            except Exception as e:
                print(f"[linkedin] keyword={keyword} (global) failed: {e}")

            # Also search explicitly remote
            time.sleep(random.uniform(1, 3))
            try:
                df2 = scrape_jobs(
                    site_name=["linkedin"],
                    search_term=keyword,
                    is_remote=True,
                    results_wanted=min(max_results, 25),
                    hours_old=720,  # 30 days
                    description_format="markdown",
                )
                all_jobs.extend(self._df_to_jobs(df2, seen_urls))
                print(f"[linkedin] remote '{keyword}': {len(df2) if df2 is not None else 0} results")
            except Exception as e:
                print(f"[linkedin] keyword={keyword} (remote) failed: {e}")

        print(f"[linkedin] Total: {len(all_jobs)} jobs")
        return all_jobs

    def _df_to_jobs(self, df, seen_urls: set) -> list[Job]:
        if df is None or df.empty:
            return []

        jobs = []
        for _, row in df.iterrows():
            url = str(row.get("job_url", "") or "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            salary = self._parse_salary(row)

            jobs.append(Job(
                id=generate_job_id(self.source_name, url),
                source=self.source_name,
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
