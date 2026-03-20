"""
Phase 1: This Phase Collects all Boil Water Advisory/Order URLs from KDHE website
         It check the response of each link before scraping and goes untill the 
         last advisory notice link.
Author: Arun Rimal
"""

import os
import json
import time
import logging
import requests
from logger_config import setup_logger
from datetime import datetime
from bs4 import BeautifulSoup

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

# ----------------------------- Configuration --------------------------------------------

BASE_URL = "https://www.kdhe.ks.gov/m/newsflash/Home/Items?cat=29&page={}&sortBy=Category"
OUTPUT_FOLDER = ROOT / "data" / "scraped_json"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

# -------------- Logger ------------------------
 
# Retrieved here at module level
logger = logging.getLogger("kdhe_pipeline")

# -------------- Helper Functions ---------------

def build_full_url(href):
    """
    This Function Builds a full URL from a relative or absolute href string.
    """
    if href.startswith("/"):
        return f"https://www.kdhe.ks.gov{href}"
    elif href.startswith("http"):
        return href
    return f"https://www.kdhe.ks.gov/{href}"


def extract_paragraph(link):
    """
    This Function Extracts and trims the paragraph text from an alert div,
    cutting off at 'For consumer questions,' if present.
    """
    paragraph = link.find("p", class_="mb-0")
    if not paragraph:
        return ""
    text = paragraph.get_text(strip=True)
    return text.split("For consumer questions,")[0] if "For consumer questions," in text else text


def extract_posted_on(link):
    """
    This Function Extracts the posted date string from the article footer div.
    Returns None if not found.
    """
    footer = link.find("div", class_="article-list-footer mt-auto")
    if not footer:
        return None
    footer_divs = footer.find_all("div")
    return footer_divs[1].get_text(strip=True) if len(footer_divs) >= 2 else None


def parse_alert(link):
    """
    This Function Parses a single alert div into a structured dictionary.
    Returns None if no anchor tag is found.
    """
    anchor = link.find("a", href=True)
    if not anchor:
        return None

    return {
        "url": build_full_url(anchor.get("href", "")),
        "title": anchor.get_text(strip=True),
        "paragraph": extract_paragraph(link),
        "posted_on": extract_posted_on(link),
        "scraped_at": datetime.now().isoformat()
    }


def deduplicate(items):
    """
    This Function Removes duplicate entries based on URL.
    """
    seen = set()
    unique = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique


# -------- Core Scraping Functions --------

def scrape_page(page_url):
    """
    This Function Fetches a single KDHE page and extracts all advisory/order records.
    Returns a list of unique advisory dictionaries, or empty list on failure.
    """
    logger.info(f"Fetching page: {page_url}")

    try:
        response = requests.get(page_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        logger.info(f"Page loaded successfully (Status: {response.status_code})")
    except requests.RequestException as e:
        logger.error(f"Failed to fetch page: {e}")
        return []

    try:
        soup = BeautifulSoup(response.content, "html.parser")
        alert_divs = soup.find_all(
            "div",
            class_="col-sm-8 col-md-9 d-flex flex-column justify-content-between"
        )
        logger.info(f"Found {len(alert_divs)} alert divs on page")

        records = [parse_alert(div) for div in alert_divs]
        records = [r for r in records if r is not None]
        unique_records = deduplicate(records)

        logger.info(f"Collected {len(records)} records | {len(unique_records)} unique")
        return unique_records

    except Exception as e:
        logger.error(f"Failed to parse page content: {e}")
        return []


def save_page_results(records, page_number):
    """
    This Function Saves a page's records to both JSON and TXT files in the output folder.
    """
    json_file = os.path.join(OUTPUT_FOLDER, f"bwa_urls_page_{page_number}.json")
    txt_file = os.path.join(OUTPUT_FOLDER, f"bwa_urls_page_{page_number}.txt")

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved JSON: {json_file}")

    with open(txt_file, "w", encoding="utf-8") as f:
        for item in records:
            f.write(f"{item['url']}\n")
    logger.info(f"Saved TXT:  {txt_file}")


# -------- Main --------

def main():

    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - URL COLLECTOR")
    logger.info("Phase 1: Collecting all notice URLs")
    logger.info("=" * 60)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    page_number = 0
    total_collected = 0

    while True:
        page_url = BASE_URL.format(page_number)

        # Check if page exists before scraping
        try:
            response = requests.get(page_url, headers=HEADERS, timeout=30)
            if response.status_code != 200:
                logger.info(f"Page {page_number} returned {response.status_code} — stopping.")
                break
        except requests.RequestException as e:
            logger.error(f"Could not reach page {page_number}: {e}")
            break

        records = scrape_page(page_url)

        if not records:
            logger.info(f"No records found on page {page_number} — stopping.")
            break

        save_page_results(records, page_number + 1)
        total_collected += len(records)

        logger.info(f"Page {page_number + 1} done. Running total: {total_collected} records.")

        page_number += 1
        time.sleep(2)

    logger.info("=" * 60)
    logger.info(f"Phase 1 Complete. Total records collected: {total_collected}")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":

    # Initialize the logger instance
    setup_logger()
    main()