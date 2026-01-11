"""
Test script for Python.org scraper
"""

import logging
from config import ScraperConfig
from python_org_scraper import PythonOrgScraper
from csv_manager import CSVManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_python_org_scraper():
    """Test Python.org scraper"""

    logger.info("=" * 60)
    logger.info("Testing Python.org Job Board Scraper")
    logger.info("=" * 60)

    # Create config
    config = ScraperConfig(
        keywords=["Python Developer"],
        locations=["Remote"],
        max_jobs_per_platform=10,  # Test with 10 jobs
        headless=False,  # Visible browser for testing
        delay_between_requests=2.0
    )

    # Create scraper
    scraper = PythonOrgScraper(config)

    # Run scraper
    logger.info("\nStarting scraper...")
    jobs = scraper.run()

    # Display results
    logger.info(f"\n✅ Found {len(jobs)} jobs from Python.org")

    if jobs:
        logger.info("\n" + "=" * 60)
        logger.info("Sample Jobs:")
        logger.info("=" * 60)

        for i, job in enumerate(jobs[:5], 1):
            logger.info(f"\n{i}. {job.title}")
            logger.info(f"   Company: {job.company}")
            logger.info(f"   Location: {job.location}")
            logger.info(f"   Type: {job.job_type} | Level: {job.experience_level}")
            logger.info(f"   Remote: {job.remote_type}")
            logger.info(f"   Posted: {job.posted_date}")
            logger.info(f"   URL: {job.apply_url}")

            if job.description:
                logger.info(f"   Contact Info:")
                for line in job.description.split('\n'):
                    logger.info(f"     {line}")

        # Save to CSV
        csv_manager = CSVManager("test_output")
        filepath = csv_manager.save_jobs(jobs, "python_org_test.csv")
        logger.info(f"\n✅ Jobs saved to: {filepath}")

        stats_file = csv_manager.save_stats([scraper.stats], "python_org_stats.csv")
        logger.info(f"✅ Stats saved to: {stats_file}")

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Summary:")
        logger.info("=" * 60)
        logger.info(f"Total jobs: {len(jobs)}")
        logger.info(f"Remote jobs: {sum(1 for j in jobs if j.remote_type == 'remote')}")
        logger.info(f"With contact info: {sum(1 for j in jobs if j.description)}")
        logger.info(f"Duration: {scraper.stats.duration_seconds():.1f}s")

    else:
        logger.warning("\n⚠️  No jobs found")
        logger.info("This might happen if:")
        logger.info("- No jobs match your criteria")
        logger.info("- Python.org is down")
        logger.info("- Page structure changed")

    logger.info("\n" + "=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)

    return jobs


def main():
    """Run test"""

    try:
        jobs = test_python_org_scraper()

        if jobs:
            logger.info("\n✅ Python.org scraper is working!")
            logger.info("\nYou can now:")
            logger.info("1. Enable it in scraper_config.json")
            logger.info("2. Run: python main.py")
        else:
            logger.warning("\n⚠️  Test completed but no jobs found")

    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()