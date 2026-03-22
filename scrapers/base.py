"""
Abstract base class for all job scrapers.
"""

from abc import ABC, abstractmethod
from typing import List
from threading import Thread
from processor.normalizer import Job

SCRAPER_TIMEOUT = 90  # seconds per scraper (needs to be higher for Playwright)


class BaseJobScraper(ABC):
    source_name: str = ""

    @abstractmethod
    def scrape(self, keywords: list[str], max_results: int = 50) -> List[Job]:
        """Scrape jobs matching keywords. Return normalized Job objects."""
        ...

    def safe_scrape(self, keywords: list[str], max_results: int = 50) -> List[Job]:
        """Wrap scrape() with error handling + timeout. Never raises."""
        results = []
        error = [None]

        def target():
            try:
                results.extend(self.scrape(keywords, max_results))
            except Exception as e:
                error[0] = e

        thread = Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=SCRAPER_TIMEOUT)

        if thread.is_alive():
            print(f"[{self.source_name}] ✗ Timed out after {SCRAPER_TIMEOUT}s")
            return []
        if error[0]:
            print(f"[{self.source_name}] ✗ Failed: {error[0]}")
            return []

        print(f"[{self.source_name}] ✓ {len(results)} jobs scraped")
        return results
