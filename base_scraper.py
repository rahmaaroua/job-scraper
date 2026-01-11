from abc import ABC, abstractmethod
from typing import List, Optional
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from models import JobListing, ScraperStats
from config import ScraperConfig
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class BaseScraper(ABC):
    """Base class for all job scrapers"""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.driver: Optional[webdriver.Chrome] = None
        self.stats = ScraperStats(
            platform=self.platform_name(),
            start_time=datetime.now()
        )

    @abstractmethod
    def platform_name(self) -> str:
        """Return the name of the platform"""
        pass

    @abstractmethod
    def scrape_jobs(self, keyword: str, location: str) -> List[JobListing]:
        """Scrape jobs for a given keyword and location"""
        pass

    def initialize_driver(self):
        """Initialize Selenium WebDriver"""
        try:
            options = Options()

            if self.config.headless:
                options.add_argument('--headless=new')

            # Additional options for stability
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')

            # Disable images for faster loading
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # Try to get the correct ChromeDriver
            try:
                service = Service(ChromeDriverManager().install())
            except Exception as driver_error:
                self.logger.warning(f"ChromeDriverManager failed: {driver_error}")
                # Try without specifying service (use system PATH)
                service = None

            if service:
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_page_load_timeout(self.config.browser_timeout)

            self.logger.info(f"WebDriver initialized for {self.platform_name()}")

        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            self.stats.errors += 1
            self.stats.error_messages.append(f"WebDriver init error: {str(e)}")
            raise

    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed")
            except Exception as e:
                self.logger.warning(f"Error closing WebDriver: {e}")

    def wait_for_element(self, by: By, value: str, timeout: int = 10):
        """Wait for an element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except Exception as e:
            self.logger.warning(f"Element not found: {value} - {e}")
            return None

    def safe_find_element(self, by: By, value: str, parent=None):
        """Safely find an element without throwing exception"""
        try:
            if parent:
                return parent.find_element(by, value)
            return self.driver.find_element(by, value)
        except:
            return None

    def safe_get_text(self, element) -> str:
        """Safely get text from an element"""
        try:
            return element.text.strip() if element else ""
        except:
            return ""

    def safe_get_attribute(self, element, attribute: str) -> str:
        """Safely get an attribute from an element"""
        try:
            return element.get_attribute(attribute) if element else ""
        except:
            return ""

    def apply_rate_limit(self):
        """Apply rate limiting delay"""
        time.sleep(self.config.delay_between_requests)

    def run(self) -> List[JobListing]:
        """Main execution method"""
        all_jobs = []

        try:
            self.initialize_driver()

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

                    # Apply delay between searches
                    self.apply_rate_limit()

            self.stats.jobs_saved = len(all_jobs)

        except Exception as e:
            self.logger.error(f"Fatal error in scraper: {e}")
            self.stats.errors += 1
            self.stats.error_messages.append(f"Fatal: {str(e)}")

        finally:
            self.close_driver()
            self.stats.end_time = datetime.now()
            self.logger.info(f"Scraping completed. Found {self.stats.jobs_found} jobs")

        return all_jobs

    def parse_salary(self, salary_text: str) -> tuple:
        """Parse salary text into min/max values"""
        import re

        if not salary_text:
            return None, None

        # Remove common words
        salary_text = salary_text.lower().replace('a year', '').replace('an hour', '')
        salary_text = salary_text.replace(',', '').replace('$', '')

        # Find all numbers
        numbers = re.findall(r'\d+\.?\d*', salary_text)

        if len(numbers) >= 2:
            return float(numbers[0]), float(numbers[1])
        elif len(numbers) == 1:
            return float(numbers[0]), float(numbers[0])

        return None, None