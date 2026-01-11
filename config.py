import os
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ScraperConfig:
    """Configuration for the job scraper"""

    # Search parameters
    keywords: List[str] = None
    locations: List[str] = None
    max_jobs_per_platform: int = 50

    # Platform settings
    platforms: Dict[str, bool] = None

    # Scraper mode
    use_enhanced_scraper: bool = False  # Set True for full details (slower)

    # Browser settings
    headless: bool = True
    browser_timeout: int = 30

    # Rate limiting
    delay_between_requests: float = 2.0
    delay_between_platforms: float = 5.0

    # Authentication (for LinkedIn/Glassdoor)
    linkedin_email: str = ""
    linkedin_password: str = ""
    glassdoor_email: str = ""
    glassdoor_password: str = ""

    # API Keys
    jsearch_api_key: str = ""

    # Output settings
    output_dir: str = "output"

    def __post_init__(self):
        """Initialize default values if not provided"""
        if self.keywords is None:
            self.keywords = ["Python Developer", "Data Scientist"]

        if self.locations is None:
            self.locations = ["United States", "Remote"]

        if self.platforms is None:
            self.platforms = {
                "indeed": True,
                "linkedin": True,  # Requires login
                "glassdoor": True,  # Requires login
                "jsearch": True,  # Requires API key
                "python_org": True  # Python.org jobs board
            }

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Load credentials from environment variables if available
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL", self.linkedin_email)
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD", self.linkedin_password)
        self.glassdoor_email = os.getenv("GLASSDOOR_EMAIL", self.glassdoor_email)
        self.glassdoor_password = os.getenv("GLASSDOOR_PASSWORD", self.glassdoor_password)
        self.jsearch_api_key = os.getenv("JSEARCH_API_KEY", self.jsearch_api_key)

    def __post_init__(self):
        """Initialize default values if not provided"""
        if self.keywords is None:
            self.keywords = ["Python Developer", "Data Scientist"]

        if self.locations is None:
            self.locations = ["United States", "Remote"]

        if self.platforms is None:
            self.platforms = {
                "indeed": True,
                "linkedin": False,  # Requires login
                "glassdoor": False  # Requires login
            }

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Load credentials from environment variables if available
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL", self.linkedin_email)
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD", self.linkedin_password)
        self.glassdoor_email = os.getenv("GLASSDOOR_EMAIL", self.glassdoor_email)
        self.glassdoor_password = os.getenv("GLASSDOOR_PASSWORD", self.glassdoor_password)


def load_config_from_file(config_file: str = "scraper_config.json") -> ScraperConfig:
    """Load configuration from a JSON file"""
    import json

    if not os.path.exists(config_file):
        return ScraperConfig()

    with open(config_file, 'r') as f:
        config_data = json.load(f)

    return ScraperConfig(**config_data)