"""
Python.org Jobs Board Scraper
Integrated into the main job scraper system
"""

import time
import re
import logging
from typing import List, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from base_scraper import BaseScraper
from models import JobListing

logger = logging.getLogger(__name__)


class PythonOrgScraper(BaseScraper):
    """Scraper for Python.org job board"""

    BASE_URL = "https://www.python.org/jobs/"

    def platform_name(self) -> str:
        return "python_org"

    def scrape_jobs(self, keyword: str, location: str) -> List[JobListing]:
        """
        Scrape jobs from Python.org
        Note: Python.org doesn't support keyword/location search,
        so we scrape all jobs and filter later
        """
        jobs = []
        page_number = 1
        max_pages = 5  # Limit to 5 pages to avoid over-scraping

        while len(jobs) < self.config.max_jobs_per_platform and page_number <= max_pages:
            try:
                # Build URL
                if page_number == 1:
                    url = self.BASE_URL
                else:
                    url = f"{self.BASE_URL}?page={page_number}"

                self.logger.info(f"Fetching Python.org page {page_number}: {url}")
                self.driver.get(url)
                time.sleep(3)

                # Find job listings
                job_listings = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "ol.list-recent-jobs > li"
                )

                if not job_listings:
                    self.logger.info("No more jobs found")
                    break

                self.logger.info(f"Found {len(job_listings)} listings on page {page_number}")

                for listing in job_listings:
                    if len(jobs) >= self.config.max_jobs_per_platform:
                        break

                    try:
                        job = self.extract_job_from_listing(listing, keyword, location)
                        if job and self.matches_criteria(job, keyword, location):
                            jobs.append(job)
                    except Exception as e:
                        self.logger.warning(f"Error extracting job: {e}")
                        continue

                page_number += 1
                self.apply_rate_limit()

            except Exception as e:
                self.logger.error(f"Error on page {page_number}: {e}")
                break

        return jobs

    def extract_job_from_listing(self, listing, keyword: str, location: str) -> Optional[JobListing]:
        """Extract job details from a listing element"""

        job_data = {
            "title": "N/A",
            "company": "N/A",
            "location": "N/A",
            "job_type": "N/A",
            "posted_date": "N/A",
            "job_url": "N/A",
            "email": "N/A",
            "website": "N/A",
            "contact_name": "N/A",
            "description": ""
        }

        # Extract title and URL
        try:
            title_element = listing.find_element(By.CSS_SELECTOR, "h2 a")
            job_data["title"] = title_element.text
            job_data["job_url"] = title_element.get_attribute("href")
        except NoSuchElementException:
            return None

        # Extract company
        try:
            job_data["company"] = listing.find_element(
                By.CSS_SELECTOR,
                "span.listing-company-name"
            ).text
        except NoSuchElementException:
            pass

        # Extract location
        try:
            job_data["location"] = listing.find_element(
                By.CSS_SELECTOR,
                "span.listing-location"
            ).text
        except NoSuchElementException:
            pass

        # Extract job type
        try:
            job_data["job_type"] = listing.find_element(
                By.CSS_SELECTOR,
                "span.listing-job-type"
            ).text
        except NoSuchElementException:
            pass

        # Extract date
        try:
            date_element = listing.find_element(By.TAG_NAME, "time")
            job_data["posted_date"] = (
                    date_element.get_attribute("datetime") or date_element.text
            )
        except NoSuchElementException:
            pass

        # Get detailed information from job page
        if job_data["job_url"] != "N/A":
            self.extract_job_details(job_data)

        # Create JobListing object
        return self.create_job_listing(job_data)

    def extract_job_details(self, job_data: dict):
        """Navigate to job page and extract detailed information"""

        try:
            self.logger.debug(f"Analyzing detail page: {job_data['job_url']}")
            self.driver.get(job_data["job_url"])
            time.sleep(2)

            # Get full page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Extract description (first paragraph or section)
            try:
                description_elem = self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.job-description, div.content"
                )
                job_data["description"] = description_elem.text[:500]  # Limit to 500 chars
            except:
                job_data["description"] = page_text[:500]

            # Extract email
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', page_text)
            if email_match:
                job_data["email"] = email_match.group(0)

            # Extract website
            web_match = re.search(r'https?://[^\s<>"\'\)]+', page_text)
            if web_match:
                job_data["website"] = web_match.group(0)

            # Extract contact name
            contact_name = self.extract_contact_name(page_text)
            if contact_name:
                job_data["contact_name"] = contact_name

            self.logger.debug("Contact information extracted")

            # Go back to listing page
            self.driver.back()
            time.sleep(2)

        except Exception as e:
            self.logger.warning(f"Error extracting details: {e}")

    def extract_contact_name(self, page_text: str) -> Optional[str]:
        """Extract contact name from page text"""

        # Try different contact patterns
        contact_selectors = [
            "//h2[contains(text(), 'Contact')]/following-sibling::*[1]",
            "//h3[contains(text(), 'Contact')]/following-sibling::*[1]",
            "//div[contains(., 'Contact Info')]",
            "//div[contains(., 'How to Apply')]"
        ]

        for selector in contact_selectors:
            try:
                contact_element = self.driver.find_element(By.XPATH, selector)
                contact_block = contact_element.text.strip()

                if contact_block and len(contact_block) > 10:
                    # Extract name from contact block
                    lines = contact_block.split('\n')
                    for line in lines:
                        if line.lower().startswith('contact:'):
                            name = line.split(':', 1)[1].strip()
                            return name
            except NoSuchElementException:
                continue

        return None

    def create_job_listing(self, job_data: dict) -> JobListing:
        """Create JobListing object from extracted data"""

        # Detect remote type
        location_text = f"{job_data['location']} {job_data['description']}".lower()
        remote_type = "on-site"
        if any(word in location_text for word in ["remote", "work from home", "wfh"]):
            remote_type = "remote"
        elif "hybrid" in location_text:
            remote_type = "hybrid"

        # Map job type
        job_type_map = {
            "full-time": "full-time",
            "part-time": "part-time",
            "contract": "contract",
            "freelance": "contract"
        }
        job_type = job_type_map.get(
            job_data["job_type"].lower(),
            "full-time"
        )

        # Detect experience level
        title_desc = f"{job_data['title']} {job_data['description']}".lower()
        experience_level = "mid"
        if any(word in title_desc for word in ["senior", "lead", "principal"]):
            experience_level = "senior"
        elif any(word in title_desc for word in ["junior", "entry", "intern"]):
            experience_level = "entry"

        # Build requirements string
        requirements = []
        if job_data["email"] != "N/A":
            requirements.append(f"Email: {job_data['email']}")
        if job_data["contact_name"] != "N/A":
            requirements.append(f"Contact: {job_data['contact_name']}")

        requirements_str = " | ".join(requirements) if requirements else None

        # Generate job ID
        job_id = f"python_org_{int(time.time() * 1000)}"

        return JobListing(
            job_id=job_id,
            platform="python_org",
            title=job_data["title"],
            company=job_data["company"],
            location=job_data["location"],
            salary_min=None,  # Python.org doesn't show salaries
            salary_max=None,
            job_type=job_type,
            experience_level=experience_level,
            remote_type=remote_type,
            description=job_data["description"],
            requirements=requirements_str,
            skills="Python",  # All jobs are Python-related
            apply_url=job_data["job_url"],
            posted_date=job_data["posted_date"],
            company_rating=None
        )

    def matches_criteria(self, job: JobListing, keyword: str, location: str) -> bool:
        """
        Check if job matches search criteria
        (Python.org doesn't have search, so we filter manually)
        """

        # Check keyword match
        keyword_lower = keyword.lower()
        searchable_text = f"{job.title} {job.description}".lower()

        # Split keyword into words and check if any match
        keyword_words = keyword_lower.split()
        keyword_match = any(word in searchable_text for word in keyword_words)

        # Check location match
        location_lower = location.lower()
        job_location_lower = job.location.lower()

        # Special handling for "Remote"
        if location_lower == "remote":
            location_match = job.remote_type == "remote"
        # Special handling for countries
        elif location_lower in ["united states", "usa", "us"]:
            location_match = any(term in job_location_lower for term in ["usa", "us", "united states", "remote"])
        else:
            location_match = location_lower in job_location_lower or job.remote_type == "remote"

        return keyword_match and location_match