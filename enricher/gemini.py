"""
Optional Gemini Flash enrichment for new jobs.
Only called if GEMINI_API_KEY is set in environment.
"""

import os
import json

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from processor.normalizer import Job


EXTRACT_PROMPT = """
Extract structured information from this job description.
Return ONLY valid JSON, no markdown, no explanation.

Schema:
{
  "required_skills": ["skill1", "skill2"],
  "years_experience": "2-4 years" or "senior" or "N/A",
  "salary_range": "$X - $Y/month" or "N/A",
  "key_highlights": ["highlight1", "highlight2"],
  "seniority": "junior" | "mid" | "senior" | "lead" | "N/A"
}

Job Description (max 2000 chars):
"""


def enrich_jobs(new_jobs: list[Job]) -> list[Job]:
    """Enrich new jobs with Gemini-extracted info. Silently skips if no API key."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[gemini] GEMINI_API_KEY not set — skipping enrichment")
        return new_jobs

    if not GENAI_AVAILABLE:
        print("[gemini] google-generativeai not installed — skipping enrichment")
        return new_jobs

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    enriched_count = 0

    for job in new_jobs:
        if not job.description_snippet:
            continue
        try:
            response = model.generate_content(
                EXTRACT_PROMPT + job.description_snippet[:2000]
            )
            # Parse response — strip markdown code fences if present
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0] if "```" in text else text
            extracted = json.loads(text)

            # Merge extracted skills into tags (dedup)
            new_tags = [s.lower() for s in extracted.get("required_skills", []) if s]
            existing_tags = set(job.tags)
            for tag in new_tags:
                if tag not in existing_tags:
                    job.tags.append(tag)
                    existing_tags.add(tag)

            # Add seniority to tags if meaningful
            seniority = extracted.get("seniority", "N/A")
            if seniority and seniority != "N/A" and seniority not in existing_tags:
                job.tags.append(seniority)

            enriched_count += 1
        except Exception as e:
            print(f"[gemini] enrichment failed for {job.id}: {e}")
            continue

    print(f"[gemini] ✓ Enriched {enriched_count}/{len(new_jobs)} jobs")
    return new_jobs
