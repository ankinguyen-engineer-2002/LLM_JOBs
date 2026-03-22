"""
Gemini Flash 2.5 enrichment — batch-processes jobs to normalize and enrich data.
Extracts: level, experience_years, job_category, employment_type, clean_tags.
"""

import os
import json
import time

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


BATCH_PROMPT = """You are a job data normalizer. For each job below, extract structured fields.
Return ONLY a JSON array with one object per job, in the same order.

For each job, return:
{
  "level": "Junior" | "Mid" | "Senior" | "Lead" | "Manager" | "Director" | "N/A",
  "experience_years": "0-1" | "1-3" | "3-5" | "5-10" | "10+" | "N/A",
  "job_category": "Data Engineering" | "ML/AI" | "Analytics" | "DevOps" | "Software Dev" | "AI/LLM" | "Other",
  "employment_type": "Full-time" | "Part-time" | "Contract" | "Freelance" | "Internship" | "N/A",
  "clean_tags": ["only_tech_skills_in_english_lowercase"]
}

Rules for clean_tags:
- ONLY include technical skills/tools (python, sql, spark, aws, docker, etc.)
- REMOVE non-tech tags like "nghỉ thứ 7", "2 năm kinh nghiệm", "it - phần mềm"
- Normalize to lowercase English
- Max 8 tags per job

Rules for level:
- "Fresher" or "Junior" → "Junior"
- "Middle" or "Mid-level" → "Mid"
- "Senior" or "Expert" → "Senior"
- If title says "Lead" or "Principal" → "Lead"
- If title says "Manager" or "Head" → "Manager"

Jobs to process:
"""


def enrich_jobs_batch(jobs_data: list[dict], api_key: str = None) -> list[dict]:
    """Enrich jobs using Gemini Flash 2.5 batch processing."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[gemini] GEMINI_API_KEY not set — skipping enrichment")
        return jobs_data

    if not GENAI_AVAILABLE:
        print("[gemini] google-generativeai not installed — skipping")
        return jobs_data

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    batch_size = 10
    total_enriched = 0

    for i in range(0, len(jobs_data), batch_size):
        batch = jobs_data[i:i + batch_size]

        # Build compact job summaries for the prompt
        job_summaries = []
        for idx, job in enumerate(batch):
            summary = {
                "idx": idx,
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "tags": job.get("tags", [])[:10],
                "job_type": job.get("job_type", "N/A"),
                "description": (job.get("description_snippet", "") or "")[:200],
            }
            job_summaries.append(summary)

        prompt = BATCH_PROMPT + json.dumps(job_summaries, ensure_ascii=False)

        try:
            response = model.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            if text.startswith("json"):
                text = text[4:].strip()

            enrichments = json.loads(text)

            if not isinstance(enrichments, list):
                enrichments = [enrichments]

            for idx, enrichment in enumerate(enrichments):
                if idx >= len(batch):
                    break
                job = batch[idx]

                # Apply enrichments
                if enrichment.get("level") and enrichment["level"] != "N/A":
                    job["level"] = enrichment["level"]
                else:
                    job["level"] = _guess_level(job.get("title", ""))

                if enrichment.get("experience_years"):
                    job["experience_years"] = enrichment["experience_years"]
                else:
                    job["experience_years"] = "N/A"

                if enrichment.get("job_category"):
                    job["job_category"] = enrichment["job_category"]
                else:
                    job["job_category"] = _guess_category(job.get("title", ""))

                if enrichment.get("employment_type") and enrichment["employment_type"] != "N/A":
                    job["employment_type"] = enrichment["employment_type"]
                else:
                    job["employment_type"] = _normalize_job_type(job.get("job_type", ""))

                if enrichment.get("clean_tags"):
                    job["clean_tags"] = enrichment["clean_tags"][:8]
                else:
                    job["clean_tags"] = _clean_tags_fallback(job.get("tags", []))

                total_enriched += 1

            print(f"[gemini] Batch {i // batch_size + 1}: enriched {len(enrichments)} jobs")

        except Exception as e:
            print(f"[gemini] Batch {i // batch_size + 1} failed: {e}")
            # Fallback: apply rule-based enrichment
            for job in batch:
                _apply_fallback(job)
                total_enriched += 1

        time.sleep(0.5)  # Rate limit

    # Compute freshness for all jobs
    _compute_freshness(jobs_data)

    print(f"[gemini] ✓ Enriched {total_enriched}/{len(jobs_data)} jobs total")
    return jobs_data


def _guess_level(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["fresher", "junior", "intern", "entry"]):
        return "Junior"
    if any(w in t for w in ["lead", "principal", "staff"]):
        return "Lead"
    if any(w in t for w in ["manager", "head", "director", "vp"]):
        return "Manager"
    if any(w in t for w in ["senior", "sr.", "sr ", "expert"]):
        return "Senior"
    if any(w in t for w in ["middle", "mid"]):
        return "Mid"
    return "Mid"  # Default


def _guess_category(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["data engineer", "etl", "dbt", "data platform", "data pipeline"]):
        return "Data Engineering"
    if any(w in t for w in ["ml ", "machine learning", "ai ", "nlp", "llm", "prompt", "deep learning"]):
        return "ML/AI"
    if any(w in t for w in ["analyst", "analytics", "bi ", "business intelligence"]):
        return "Analytics"
    if any(w in t for w in ["devops", "sre", "infrastructure", "cloud"]):
        return "DevOps"
    if any(w in t for w in ["ai trainer", "ai annotator", "annotation"]):
        return "AI/LLM"
    return "Data Engineering"  # Default for this project


def _normalize_job_type(raw: str) -> str:
    if not raw or raw in ("N/A", "n/a", "nan", ""):
        return "Full-time"
    r = raw.lower().strip()
    if "full" in r:
        return "Full-time"
    if "part" in r:
        return "Part-time"
    if "contract" in r or "freelance" in r:
        return "Contract"
    if "intern" in r:
        return "Internship"
    return "Full-time"


def _clean_tags_fallback(tags: list) -> list:
    """Remove non-tech Vietnamese tags."""
    tech_keywords = {
        "python", "sql", "spark", "pyspark", "dbt", "airflow", "docker",
        "kafka", "azure", "aws", "gcp", "kubernetes", "java", "scala",
        "golang", "rust", "react", "node.js", "typescript", "javascript",
        "pytorch", "tensorflow", "pandas", "numpy", "bigquery", "snowflake",
        "databricks", "tableau", "power bi", "mlflow", "ci/cd", "git",
        "postgresql", "mongodb", "redis", "elasticsearch", "hadoop",
        "data engineer", "data warehousing", "etl", "machine learning",
        "deep learning", "nlp", "computer vision", "ai", "llm",
        "data science", "analytics", "business intelligence",
        "linux", "terraform", "ansible", "jenkins", "grafana",
        "english", "big data", "data modeling", "software engineering",
    }
    return [t.lower() for t in tags if t.lower() in tech_keywords][:8]


def _apply_fallback(job: dict):
    """Rule-based fallback when Gemini fails."""
    job["level"] = _guess_level(job.get("title", ""))
    job["experience_years"] = "N/A"
    job["job_category"] = _guess_category(job.get("title", ""))
    job["employment_type"] = _normalize_job_type(job.get("job_type", ""))
    job["clean_tags"] = _clean_tags_fallback(job.get("tags", []))


def _compute_freshness(jobs_data: list[dict]):
    """Add freshness field based on scraped_at or posted_date."""
    import datetime
    now = datetime.datetime.now()
    for job in jobs_data:
        date_str = job.get("posted_date") or job.get("scraped_at") or job.get("first_seen") or ""
        if not date_str:
            job["freshness"] = "unknown"
            continue
        try:
            if "T" in date_str:
                dt = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))
            else:
                dt = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
            diff_days = (now - dt).days
            if diff_days <= 1:
                job["freshness"] = "today"
            elif diff_days <= 3:
                job["freshness"] = "3d"
            elif diff_days <= 7:
                job["freshness"] = "7d"
            elif diff_days <= 14:
                job["freshness"] = "14d"
            elif diff_days <= 30:
                job["freshness"] = "30d"
            else:
                job["freshness"] = ">30d"
        except Exception:
            job["freshness"] = "unknown"


# === STANDALONE ENRICHMENT SCRIPT ===
if __name__ == "__main__":
    import sys
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/jobs.json"

    with open(data_path, "r") as f:
        jobs = json.load(f)

    print(f"[gemini] Loading {len(jobs)} jobs from {data_path}")
    enriched = enrich_jobs_batch(jobs)

    with open(data_path, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    print(f"[gemini] ✅ Saved enriched data to {data_path}")
