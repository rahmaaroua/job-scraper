from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List
import hashlib


@dataclass
class JobListing:
    """Data model for a job listing"""

    # Core fields
    job_id: str
    platform: str
    title: str
    company: str
    location: str

    # Salary information
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"

    # Job details
    job_type: Optional[str] = None  # full-time, part-time, contract
    experience_level: Optional[str] = None  # entry, mid, senior
    remote_type: Optional[str] = None  # remote, hybrid, on-site

    # Descriptions
    description: Optional[str] = None
    requirements: Optional[str] = None
    skills: Optional[str] = None

    # Links and metadata
    apply_url: str = ""
    posted_date: Optional[str] = None
    scraped_date: str = None

    # Platform-specific
    company_rating: Optional[float] = None

    def __post_init__(self):
        """Initialize scraped_date if not provided"""
        if self.scraped_date is None:
            self.scraped_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate_hash(self) -> str:
        """Generate a unique hash for deduplication"""
        # Use title, company, and location to identify duplicates
        unique_str = f"{self.title.lower()}_{self.company.lower()}_{self.location.lower()}"
        return hashlib.md5(unique_str.encode()).hexdigest()

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
        return asdict(self)

    @classmethod
    def csv_headers(cls) -> List[str]:
        """Return CSV column headers"""
        return [
            'job_id', 'platform', 'title', 'company', 'location',
            'salary_min', 'salary_max', 'salary_currency',
            'job_type', 'experience_level', 'remote_type',
            'description', 'requirements', 'skills',
            'apply_url', 'posted_date', 'scraped_date', 'company_rating'
        ]


@dataclass
class ScraperStats:
    """Statistics for a scraping session"""

    platform: str
    start_time: datetime
    end_time: Optional[datetime] = None
    jobs_found: int = 0
    jobs_saved: int = 0
    errors: int = 0
    error_messages: List[str] = None

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []

    def duration_seconds(self) -> float:
        """Calculate scraping duration"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for logging"""
        return {
            'platform': self.platform,
            'start_time': self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            'end_time': self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            'duration_seconds': self.duration_seconds(),
            'jobs_found': self.jobs_found,
            'jobs_saved': self.jobs_saved,
            'errors': self.errors,
            'error_count': len(self.error_messages)
        }