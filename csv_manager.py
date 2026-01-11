import csv
import os
from datetime import datetime
from typing import List
import logging

from models import JobListing, ScraperStats

logger = logging.getLogger(__name__)


class CSVManager:
    """Handles CSV file operations for job listings and logs"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_filename(self, prefix: str = "jobs") -> str:
        """Generate timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.csv"

    def save_jobs(self, jobs: List[JobListing], filename: str = None) -> str:
        """Save job listings to CSV file"""
        if not jobs:
            logger.warning("No jobs to save")
            return None

        if filename is None:
            filename = self.generate_filename("jobs")

        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=JobListing.csv_headers())
                writer.writeheader()

                for job in jobs:
                    writer.writerow(job.to_dict())

            logger.info(f"Saved {len(jobs)} jobs to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving jobs to CSV: {e}")
            raise

    def save_stats(self, stats_list: List[ScraperStats], filename: str = None) -> str:
        """Save scraping statistics to CSV file"""
        if not stats_list:
            logger.warning("No stats to save")
            return None

        if filename is None:
            filename = self.generate_filename("scraper_log")

        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['platform', 'start_time', 'end_time', 'duration_seconds',
                              'jobs_found', 'jobs_saved', 'errors', 'error_count']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for stats in stats_list:
                    writer.writerow(stats.to_dict())

            logger.info(f"Saved statistics to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving stats to CSV: {e}")
            raise

    def deduplicate_jobs(self, jobs: List[JobListing]) -> List[JobListing]:
        """Remove duplicate jobs based on hash"""
        seen_hashes = set()
        unique_jobs = []

        for job in jobs:
            job_hash = job.generate_hash()
            if job_hash not in seen_hashes:
                seen_hashes.add(job_hash)
                unique_jobs.append(job)

        duplicates_removed = len(jobs) - len(unique_jobs)
        if duplicates_removed > 0:
            logger.info(f"Removed {duplicates_removed} duplicate jobs")

        return unique_jobs

    def merge_with_existing(self, new_jobs: List[JobListing],
                            existing_file: str = None) -> List[JobListing]:
        """Merge new jobs with existing CSV file, removing duplicates"""

        if existing_file and os.path.exists(existing_file):
            try:
                existing_jobs = self.load_jobs(existing_file)
                all_jobs = existing_jobs + new_jobs
                return self.deduplicate_jobs(all_jobs)
            except Exception as e:
                logger.warning(f"Could not merge with existing file: {e}")

        return self.deduplicate_jobs(new_jobs)

    def load_jobs(self, filepath: str) -> List[JobListing]:
        """Load jobs from CSV file"""
        jobs = []

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Convert empty strings to None
                    for key, value in row.items():
                        if value == '':
                            row[key] = None
                        elif key in ['salary_min', 'salary_max', 'company_rating']:
                            try:
                                row[key] = float(value) if value else None
                            except:
                                row[key] = None

                    jobs.append(JobListing(**row))

            logger.info(f"Loaded {len(jobs)} jobs from {filepath}")

        except Exception as e:
            logger.error(f"Error loading jobs from CSV: {e}")
            raise

        return jobs