"""
Complete JSearch API Scraper
Supports: LinkedIn, Glassdoor, Indeed, ZipRecruiter, Google Jobs

Usage:
    from jsearch_scraper import JSearchScraper
    scraper = JSearchScraper(config, api_key)
    jobs = scraper.run()
"""

import requests
import time
import logging
from typing import List, Optional, Dict
from datetime import datetime

from models import JobListing, ScraperStats

logger = logging.getLogger(__name__)


class JSearchScraper:
    """
    Complete JSearch API scraper with all features

    Platforms supported:
    - linkedin.com
    - glassdoor.com
    - indeed.com
    - ziprecruiter.com
    - google.com/jobs
    """

    API_URL = "https://jsearch.p.rapidapi.com/search"
    DETAILS_URL = "https://jsearch.p.rapidapi.com/job-details"

    def __init__(self, config, api_key: str, platforms: List[str] = None):
        """
        Initialize JSearch scraper

        Args:
            config: ScraperConfig object
            api_key: Your RapidAPI key for JSearch
            platforms: List of platforms to scrape (default: all)
                      Options: ['linkedin', 'glassdoor', 'indeed', 'ziprecruiter', 'google']
        """
        self.config = config
        self.api_key = api_key
        self.platforms = platforms or ['linkedin', 'glassdoor', 'indeed']

        self.logger = logging.getLogger(self.__class__.__name__)
        self.stats = ScraperStats(
            platform="jsearch",
            start_time=datetime.now()
        )

        if not self.api_key:
            raise ValueError(
                "JSearch API key required. "
                "Get it at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
            )

        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }

    def run(self) -> List[JobListing]:
        """Main execution - scrape all configured keywords and locations"""
        all_jobs = []

        try:
            for keyword in self.config.keywords:
                for location in self.config.locations:
                    self.logger.info(f"Scraping {keyword} jobs in {location}")

                    try:
                        jobs = self.scrape_jobs(keyword, location)
                        all_jobs.extend(jobs)
                        self.stats.jobs_found += len(jobs)

                        self.logger.info(f"Found {len(jobs)} jobs for {keyword} in {location}")

                    except Exception as e:
                        self.logger.error(f"Error scraping {keyword} in {location}: {e}")
                        self.stats.errors += 1
                        self.stats.error_messages.append(f"{keyword}|{location}: {str(e)}")

                    # Rate limiting
                    time.sleep(self.config.delay_between_requests)

            self.stats.jobs_saved = len(all_jobs)

        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            self.stats.errors += 1
            self.stats.error_messages.append(f"Fatal: {str(e)}")

        finally:
            self.stats.end_time = datetime.now()
            self.logger.info(f"Scraping completed. Found {self.stats.jobs_found} jobs")

        return all_jobs

    def scrape_jobs(self, keyword: str, location: str) -> List[JobListing]:
        """Scrape jobs for a specific keyword and location"""
        jobs = []
        page = 1

        while len(jobs) < self.config.max_jobs_per_platform:
            try:
                # Build search query
                query = self.build_query(keyword, location)

                params = {
                    "query": query,
                    "page": str(page),
                    "num_pages": "1",
                    "date_posted": "all"  # all, today, 3days, week, month
                }

                self.logger.info(f"Fetching page {page}...")
                response = requests.get(
                    self.API_URL,
                    headers=self.headers,
                    params=params,
                    timeout=30
                )

                # Handle rate limiting
                if response.status_code == 429:
                    self.logger.warning("Rate limit exceeded")
                    self.stats.errors += 1
                    self.stats.error_messages.append("Rate limit exceeded")
                    break

                # Handle auth errors
                if response.status_code == 403:
                    self.logger.error("API authentication failed. Check your API key.")
                    raise ValueError("Invalid API key or not subscribed to JSearch")

                response.raise_for_status()
                data = response.json()

                # Check if we have results
                if 'data' not in data or not data['data']:
                    self.logger.info("No more jobs found")
                    break

                # Parse jobs
                for job_data in data['data']:
                    if len(jobs) >= self.config.max_jobs_per_platform:
                        break

                    job = self.parse_job(job_data)
                    if job:
                        jobs.append(job)

                # Check if there are more pages
                if len(data['data']) < 10:  # JSearch returns ~10 per page
                    break

                page += 1
                time.sleep(1)  # API rate limiting

            except requests.exceptions.RequestException as e:
                self.logger.error(f"API request failed on page {page}: {e}")
                self.stats.errors += 1
                break

            except Exception as e:
                self.logger.error(f"Error on page {page}: {e}")
                self.stats.errors += 1
                break

        return jobs

    def build_query(self, keyword: str, location: str) -> str:
        """Build optimized search query"""
        # Simple query
        query = f"{keyword} in {location}"
        return query

    def parse_job(self, data: Dict) -> Optional[JobListing]:
        """Parse job data from JSearch API response"""
        try:
            # Extract basic info
            job_id = data.get('job_id', f"jsearch_{int(time.time() * 1000)}")
            title = data.get('job_title', '')
            company = data.get('employer_name', '')

            # Location
            city = data.get('job_city', '')
            state = data.get('job_state', '')
            country = data.get('job_country', '')

            location_parts = [city, state, country]
            location = ', '.join(filter(None, location_parts))

            # Salary
            salary_min = data.get('job_min_salary')
            salary_max = data.get('job_max_salary')
            salary_currency = data.get('job_salary_currency', 'USD')

            # Employment type
            employment_type = data.get('job_employment_type', '').upper()
            job_type = self.map_employment_type(employment_type)

            # Remote
            is_remote = data.get('job_is_remote', False)
            remote_type = "remote" if is_remote else "on-site"

            # Check for hybrid in title/description
            title_lower = title.lower()
            description = data.get('job_description', '')
            if 'hybrid' in title_lower or 'hybrid' in description.lower():
                remote_type = "hybrid"

            # Experience level
            experience_level = self.detect_experience_level(title, description)

            # Skills extraction
            skills = self.extract_skills(data)

            # Requirements
            requirements = data.get('job_required_experience', {}).get('required_experience_in_months')
            if requirements:
                requirements = f"{requirements} months of experience required"

            # Apply link
            apply_url = data.get('job_apply_link', '')
            if not apply_url:
                apply_url = data.get('job_google_link', '')

            # Posted date
            posted_date = data.get('job_posted_at_datetime_utc')
            if posted_date:
                # Convert to readable format
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(posted_date.replace('Z', '+00:00'))
                    posted_date = dt.strftime('%Y-%m-%d')
                except:
                    pass

            # Company rating (if from Glassdoor)
            company_rating = None
            if 'glassdoor' in apply_url.lower():
                # JSearch doesn't provide ratings directly
                # But we know it's from Glassdoor
                pass

            # Platform detection
            platform = self.detect_platform(apply_url)

            return JobListing(
                job_id=job_id,
                platform=platform,
                title=title,
                company=company,
                location=location,
                salary_min=salary_min,
                salary_max=salary_max,
                salary_currency=salary_currency,
                job_type=job_type,
                experience_level=experience_level,
                remote_type=remote_type,
                description=description,
                requirements=requirements,
                skills=skills,
                apply_url=apply_url,
                posted_date=posted_date,
                company_rating=company_rating
            )

        except Exception as e:
            self.logger.warning(f"Error parsing job: {e}")
            return None

    def map_employment_type(self, employment_type: str) -> str:
        """Map JSearch employment type to our format"""
        employment_type = employment_type.upper()

        mapping = {
            'FULLTIME': 'full-time',
            'PARTTIME': 'part-time',
            'CONTRACTOR': 'contract',
            'INTERN': 'internship'
        }

        return mapping.get(employment_type, 'full-time')

    def detect_experience_level(self, title: str, description: str) -> str:
        """Detect experience level from title and description"""
        text = f"{title} {description}".lower()

        # Senior
        senior_keywords = ['senior', 'sr.', 'lead', 'principal', 'staff', 'architect', 'director']
        if any(keyword in text for keyword in senior_keywords):
            return 'senior'

        # Entry
        entry_keywords = ['junior', 'jr.', 'entry', 'associate', 'graduate', 'intern']
        if any(keyword in text for keyword in entry_keywords):
            return 'entry'

        return 'mid'

    def extract_skills(self, data: Dict) -> Optional[str]:
        """Extract skills from job data"""
        skills_list = []

        # Check job_required_skills
        if 'job_required_skills' in data:
            skills_list.extend(data['job_required_skills'])

        # Check job_highlights (skills section)
        if 'job_highlights' in data:
            highlights = data['job_highlights']
            if 'Qualifications' in highlights:
                # Parse qualifications for skills
                pass

        # Common tech skills to look for in description
        description = data.get('job_description', '').lower()
        common_skills = [
            'python', 'java', 'javascript', 'react', 'node.js', 'angular', 'vue',
            'sql', 'postgresql', 'mongodb', 'mysql', 'redis',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes',
            'git', 'ci/cd', 'jenkins', 'terraform',
            'machine learning', 'deep learning', 'tensorflow', 'pytorch',
            'rest api', 'graphql', 'microservices'
        ]

        for skill in common_skills:
            if skill in description and skill.title() not in skills_list:
                skills_list.append(skill.title())

        return ', '.join(skills_list) if skills_list else None

    def detect_platform(self, apply_url: str) -> str:
        """Detect which platform the job is from"""
        url_lower = apply_url.lower()

        if 'linkedin' in url_lower:
            return 'linkedin'
        elif 'glassdoor' in url_lower:
            return 'glassdoor'
        elif 'indeed' in url_lower:
            return 'indeed'
        elif 'ziprecruiter' in url_lower:
            return 'ziprecruiter'
        elif 'google' in url_lower:
            return 'google_jobs'
        else:
            return 'jsearch'

    def get_job_details(self, job_id: str) -> Optional[Dict]:
        """
        Get additional job details (optional - costs extra API call)

        Args:
            job_id: Job ID from search results

        Returns:
            Detailed job information
        """
        try:
            params = {"job_id": job_id}

            response = requests.get(
                self.DETAILS_URL,
                headers=self.headers,
                params=params,
                timeout=30
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            self.logger.warning(f"Could not get details for job {job_id}: {e}")
            return None