# Job Scraper

Automated Python tool that scrapes job listings from Indeed and JSearch API. Exports to CSV with deduplication and detailed logging.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

## Configuration

Edit `scraper_config.json`:

```json
{
  "platforms": {"indeed": true, "jsearch": true},
  "search_keywords": ["python developer"],
  "locations": ["Remote"],
  "max_jobs_per_platform": 50,
  "jsearch_api_key": "YOUR_RAPIDAPI_KEY"
}
```

Get API key: [RapidAPI JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)

## Usage

```bash
python main.py
```

Output saved to `output/` directory as CSV files.

## Features

- Multi-platform scraping (Indeed, JSearch)
- Automatic deduplication
- CSV export with timestamps
- Headless browser mode
- Rate limiting
- Detailed statistics

## Requirements

- Python 3.8+
- Chrome browser

## Troubleshooting

Check `scraper.log` for errors. Set `"headless": false` in config to see browser actions.

---

For educational use only. Respect website terms of service.
