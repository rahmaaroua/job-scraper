import logging
import schedule
import time
from typing import List
from datetime import datetime

from config import ScraperConfig, load_config_from_file
from models import JobListing, ScraperStats
from csv_manager import CSVManager
from indeed_scraper import IndeedScraper
from jsearch_scraper import JSearchScraper

import os
print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir())

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class JobScraperOrchestrator:
    """Main orchestrator for the job scraping system"""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.csv_manager = CSVManager(config.output_dir)
        self.scrapers = self._initialize_scrapers()

    def _initialize_scrapers(self) -> dict:
        scrapers = {}

        # Indeed scraper
        if self.config.platforms.get("indeed", False):
            scrapers["indeed"] = IndeedScraper(self.config)
            logger.info("Using Indeed scraper")

        # JSearch scraper
        if self.config.platforms.get("jsearch", False):
            if not self.config.jsearch_api_key:
                logger.error("JSearch API key missing in config")
            else:
                scrapers["jsearch"] = JSearchScraper(
                    config=self.config,
                    api_key=self.config.jsearch_api_key
                )
                logger.info("Using JSearch scraper (RapidAPI)")

        return scrapers

    def run_scraping_session(self):
        """Execute a complete scraping session"""
        logger.info("=" * 80)
        logger.info(f"Starting scraping session at {datetime.now()}")
        logger.info("=" * 80)

        all_jobs: List[JobListing] = []
        all_stats: List[ScraperStats] = []

        # Run each enabled scraper
        for platform_name, scraper in self.scrapers.items():
            logger.info(f"\nStarting {platform_name} scraper...")

            try:
                jobs = scraper.run()
                all_jobs.extend(jobs)
                all_stats.append(scraper.stats)

                logger.info(f"{platform_name} scraper completed: {len(jobs)} jobs found")

                # Apply delay between platforms
                if len(self.scrapers) > 1:
                    logger.info(f"Waiting {self.config.delay_between_platforms}s before next platform...")
                    time.sleep(self.config.delay_between_platforms)

            except Exception as e:
                logger.error(f"Error running {platform_name} scraper: {e}")
                continue

        # Process and save results
        logger.info(f"\nProcessing {len(all_jobs)} total jobs...")

        # Deduplicate jobs
        unique_jobs = self.csv_manager.deduplicate_jobs(all_jobs)
        logger.info(f"After deduplication: {len(unique_jobs)} unique jobs")

        # Save to CSV
        if unique_jobs:
            jobs_file = self.csv_manager.save_jobs(unique_jobs)
            logger.info(f"Jobs saved to: {jobs_file}")
        else:
            logger.warning("No jobs to save!")

        # Save statistics
        if all_stats:
            stats_file = self.csv_manager.save_stats(all_stats)
            logger.info(f"Statistics saved to: {stats_file}")

        # Print summary
        self._print_summary(unique_jobs, all_stats)

        logger.info("=" * 80)
        logger.info("Scraping session completed")
        logger.info("=" * 80)

        return unique_jobs

    def _print_summary(self, jobs: List[JobListing], stats: List[ScraperStats]):
        """Print a summary of the scraping session"""
        logger.info("\n" + "=" * 80)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 80)

        # Overall stats
        total_found = sum(s.jobs_found for s in stats)
        total_errors = sum(s.errors for s in stats)
        total_duration = sum(s.duration_seconds() for s in stats)

        logger.info(f"Total jobs found: {total_found}")
        logger.info(f"Unique jobs saved: {len(jobs)}")
        logger.info(f"Total errors: {total_errors}")
        logger.info(f"Total duration: {total_duration:.2f} seconds")

        # Per-platform breakdown
        logger.info("\nPer-Platform Results:")
        for stat in stats:
            logger.info(f"  {stat.platform}:")
            logger.info(f"    Jobs: {stat.jobs_found}")
            logger.info(f"    Errors: {stat.errors}")
            logger.info(f"    Duration: {stat.duration_seconds():.2f}s")

        # Job type distribution
        if jobs:
            logger.info("\nJob Distribution:")

            # By platform
            platform_counts = {}
            for job in jobs:
                platform_counts[job.platform] = platform_counts.get(job.platform, 0) + 1
            for platform, count in platform_counts.items():
                logger.info(f"  {platform}: {count} jobs")

            # By job type
            type_counts = {}
            for job in jobs:
                job_type = job.job_type or "unknown"
                type_counts[job_type] = type_counts.get(job_type, 0) + 1
            logger.info("\n  Job Types:")
            for jtype, count in type_counts.items():
                logger.info(f"    {jtype}: {count}")

            # Remote distribution
            remote_counts = {}
            for job in jobs:
                remote = job.remote_type or "unknown"
                remote_counts[remote] = remote_counts.get(remote, 0) + 1
            logger.info("\n  Remote Types:")
            for rtype, count in remote_counts.items():
                logger.info(f"    {rtype}: {count}")

        logger.info("=" * 80 + "\n")

    def schedule_scraping(self, interval_hours: int = 6):
        """Schedule periodic scraping"""
        logger.info(f"Scheduling scraping every {interval_hours} hours")

        # Run immediately
        self.run_scraping_session()

        # Schedule future runs
        schedule.every(interval_hours).hours.do(self.run_scraping_session)

        logger.info("Scheduler started. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")


def main():
    """Main entry point"""

    # Load configuration
    try:
        config = load_config_from_file("scraper_config.json")
    except:
        logger.info("Config file not found, using default configuration")
        config = ScraperConfig()

    # Create orchestrator
    orchestrator = JobScraperOrchestrator(config)

    # Run scraping (single run)
    orchestrator.run_scraping_session()

    # For scheduled runs, use:
    # orchestrator.schedule_scraping(interval_hours=6)


if __name__ == "__main__":
    main()