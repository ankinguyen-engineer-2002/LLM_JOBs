"""
VietnamWorks scraper — Vietnamese job board.
VietnamWorks is a Next.js SPA that requires JavaScript for rendering.
This scraper uses the Google Jobs cache / web search as a workaround,
or directly fetches the search page and looks for embedded JSON data.
"""

import requests
import re
import json
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime
from bs4 import BeautifulSoup


class VietnamWorksScraper(BaseJobScraper):
    source_name = "vietnamworks"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            # Method 1: Try the homepage/search variants that might have preloaded data
            for url_template in [
                "https://www.vietnamworks.com/viec-lam-{slug}-tai-viet-nam",
                "https://www.vietnamworks.com/nganh-nghe/{slug}-viec-lam",
                "https://www.vietnamworks.com/{slug}-jobs",
            ]:
                slug = keyword.lower().replace(" ", "-")
                url = url_template.format(slug=slug)

                try:
                    resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                    if resp.status_code != 200:
                        continue
                except requests.RequestException:
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Look for __NEXT_DATA__
                nd = soup.select_one("script#__NEXT_DATA__")
                if nd:
                    try:
                        data = json.loads(nd.get_text())
                        new_jobs = self._parse_next_data(data, keyword, seen_urls)
                        jobs.extend(new_jobs)
                        if new_jobs:
                            break
                    except (json.JSONDecodeError, KeyError):
                        pass

                # Look for job-like elements
                cards = (soup.select("[class*='JobItem']") or
                         soup.select("[class*='job-item']") or
                         soup.select("article"))
                for card in cards:
                    job = self._parse_html_card(card, keyword, seen_urls)
                    if job:
                        jobs.append(job)

                if jobs:
                    break

            if len(jobs) >= max_results:
                break

        if not jobs:
            print("[vietnamworks] No jobs found — site requires JS rendering")

        return jobs[:max_results]

    def _parse_next_data(self, data: dict, keyword: str, seen_urls: set) -> list[Job]:
        """Extract jobs from Next.js __NEXT_DATA__ JSON."""
        jobs = []
        # Walk through the data looking for job arrays
        found_items = self._find_job_arrays(data)

        for item in found_items:
            if not isinstance(item, dict):
                continue
            title = item.get("jobTitle", "") or item.get("title", "")
            if not title:
                continue

            job_id = str(item.get("jobId", "") or item.get("id", ""))
            alias = item.get("alias", "") or item.get("slug", "") or job_id
            url = f"https://www.vietnamworks.com/viec-lam/{alias}-jv"
            if url in seen_urls:
                continue
            seen_urls.add(url)

            company = "N/A"
            co = item.get("company", item.get("companyName", ""))
            if isinstance(co, dict):
                company = co.get("companyName", co.get("name", "N/A"))
            elif isinstance(co, str) and co:
                company = co

            locations = item.get("workingLocations", [])
            if isinstance(locations, list) and locations:
                loc_names = []
                for l in locations[:2]:
                    if isinstance(l, dict):
                        loc_names.append(l.get("cityName", l.get("name", "")))
                    elif isinstance(l, str):
                        loc_names.append(l)
                location = ", ".join(n for n in loc_names if n) or "N/A"
            else:
                location = "N/A"

            jobs.append(Job(
                id=generate_job_id(self.source_name, str(job_id or url)),
                source=self.source_name,
                url=url,
                title=title.strip(),
                company=company,
                location=location,
                is_remote="remote" in title.lower(),
                salary="N/A",
                tags=[],
                scraped_at=datetime.now().isoformat(),
                first_seen=datetime.now().isoformat(),
            ))

        return jobs

    def _find_job_arrays(self, obj, depth=0) -> list:
        if depth > 8:
            return []
        results = []
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict):
                if any("title" in item or "jobTitle" in item for item in obj if isinstance(item, dict)):
                    results.extend(obj)
            for item in obj:
                results.extend(self._find_job_arrays(item, depth + 1))
        elif isinstance(obj, dict):
            for value in obj.values():
                results.extend(self._find_job_arrays(value, depth + 1))
        return results

    def _parse_html_card(self, card, keyword: str, seen_urls: set) -> Job | None:
        """Parse an HTML job card element."""
        title_el = card.select_one("h2") or card.select_one("h3") or card.select_one("[class*='title']")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        link = card.select_one("a[href]")
        href = link.get("href", "") if link else ""
        url = href if href.startswith("http") else f"https://www.vietnamworks.com{href}"
        if url in seen_urls or not href:
            return None
        seen_urls.add(url)

        company_el = card.select_one("[class*='company']")
        company = company_el.get_text(strip=True) if company_el else "N/A"

        return Job(
            id=generate_job_id(self.source_name, url),
            source=self.source_name,
            url=url,
            title=title,
            company=company,
            location="Vietnam",
            is_remote="remote" in title.lower(),
            salary="N/A",
            tags=[],
            scraped_at=datetime.now().isoformat(),
            first_seen=datetime.now().isoformat(),
        )
