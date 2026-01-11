from typing import List
from urllib.parse import quote_plus
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time

from base_scraper import BaseScraper
from models import JobListing


class IndeedScraper(BaseScraper):
    """Scraper for Indeed.com"""

    BASE_URL = "https://www.indeed.com"

    def platform_name(self) -> str:
        return "indeed"

    def build_search_url(self, keyword: str, location: str, start: int = 0) -> str:
        """Build the Indeed search URL"""
        keyword_encoded = quote_plus(keyword)
        location_encoded = quote_plus(location)
        return f"{self.BASE_URL}/jobs?q={keyword_encoded}&l={location_encoded}&start={start}"

    def scrape_jobs(self, keyword: str, location: str) -> List[JobListing]:
        """Scrape jobs from Indeed"""
        jobs = []
        page = 0

        while len(jobs) < self.config.max_jobs_per_platform:
            try:
                url = self.build_search_url(keyword, location, page * 10)
                self.logger.info(f"Fetching: {url}")
                self.driver.get(url)

                # Wait for job cards to load
                time.sleep(3)

                # Find all job cards
                try:
                    job_cards = self.driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")

                    if not job_cards:
                        self.logger.info("No more jobs found")
                        break

                    for card in job_cards:
                        if len(jobs) >= self.config.max_jobs_per_platform:
                            break

                        try:
                            job = self.extract_job_from_card(card, keyword, location)
                            if job:
                                jobs.append(job)
                        except Exception as e:
                            self.logger.warning(f"Error extracting job: {e}")
                            continue

                    page += 1
                    self.apply_rate_limit()

                except Exception as e:
                    self.logger.error(f"Error finding job cards: {e}")
                    break

            except TimeoutException:
                self.logger.warning(f"Timeout loading page {page}")
                break
            except Exception as e:
                self.logger.error(f"Error on page {page}: {e}")
                break

        return jobs

    def extract_job_from_card(self, card, keyword: str, location: str) -> JobListing:
        """Extract job details from a job card"""

        # Job ID
        job_id = self.safe_get_attribute(card, "data-jk")
        if not job_id:
            job_id = f"indeed_{int(time.time() * 1000)}"

        # Title
        title_elem = self.safe_find_element(By.CSS_SELECTOR, "h2.jobTitle span", card)
        title = self.safe_get_text(title_elem)

        # Company
        company_elem = self.safe_find_element(By.CSS_SELECTOR, "span[data-testid='company-name']", card)
        company = self.safe_get_text(company_elem)

        # Location
        location_elem = self.safe_find_element(By.CSS_SELECTOR, "div[data-testid='text-location']", card)
        job_location = self.safe_get_text(location_elem)

        # Salary
        salary_elem = self.safe_find_element(By.CSS_SELECTOR, "div[data-testid='attribute_snippet_testid']", card)
        salary_text = self.safe_get_text(salary_elem)
        salary_min, salary_max = self.parse_salary(salary_text)

        # Job snippet (short description)
        snippet_elem = self.safe_find_element(By.CSS_SELECTOR, "div.job-snippet", card)
        snippet = self.safe_get_text(snippet_elem)

        # Apply URL
        apply_url = f"{self.BASE_URL}/viewjob?jk={job_id}"

        # Detect remote type
        remote_type = "on-site"
        if any(word in title.lower() or word in snippet.lower() for word in ["remote", "work from home"]):
            remote_type = "remote"
        elif "hybrid" in title.lower() or "hybrid" in snippet.lower():
            remote_type = "hybrid"

        # Detect job type
        job_type = "full-time"
        snippet_lower = snippet.lower()
        if "part-time" in snippet_lower or "part time" in snippet_lower:
            job_type = "part-time"
        elif "contract" in snippet_lower or "contractor" in snippet_lower:
            job_type = "contract"

        # Detect experience level
        experience_level = "mid"
        if any(word in title.lower() or word in snippet.lower() for word in ["senior", "lead", "principal"]):
            experience_level = "senior"
        elif any(word in title.lower() or word in snippet.lower() for word in ["junior", "entry", "associate"]):
            experience_level = "entry"

        # Click to get full description (optional - can be slow)
        description = snippet
        try:
            # Try to get more details without clicking (faster)
            pass
        except:
            pass

        return JobListing(
            job_id=job_id,
            platform="indeed",
            title=title,
            company=company,
            location=job_location or location,
            salary_min=salary_min,
            salary_max=salary_max,
            job_type=job_type,
            experience_level=experience_level,
            remote_type=remote_type,
            description=description,
            requirements=None,
            skills=None,
            apply_url=apply_url,
            posted_date=None
        )