"""
Phase 2: This Phase creates new feature or key value pair as a part of feature engineering.
         It extract the useful info from the existing key value pairs to create new key value
         pairs.
"""

import os
import re
import json
import logging
from pathlib import Path
from logger_config import setup_logger
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from pathlib import Path

# -------- Configuration --------
 
ROOT = Path(__file__).resolve().parent.parent
 
INPUT_FOLDER  = ROOT / "data" / "scraped_json"
OUTPUT_FOLDER = ROOT / "data" / "processed_json"
 
TRIGGER_PHRASES = sorted([
    r"Boil Water Advisory Re-issued for",
    r"Boil Water Advisories Rescinded for",
    r"Boil Water Advisory Rescinded for the",
    r"Boil Water Advisory Rescinded for",
    r"Boil Water Advisory Issued for the",
    r"Boil Water Advisory Issued for",
    r"Boil Water Order Rescinded for the",
    r"Boil Water Order Rescinded for",
    r"Boil Water Order Issued for the",
    r"Boil Water Order Issued for",
    r"Boil Water Order for the",
    r"Boil Water Order for",
    r"Boil Water Advisory for the",
    r"Boil Water Advisory for",
], key=len, reverse=True)
 
NON_GEOCODABLE = re.compile(
    r"\b(RWD|PWS|USD|Rural Water|Water District|Co RWD|Subdivision|Unit)\b",
    re.IGNORECASE
)
 
# -------- Logger --------
 
# Retrieved here at module level — works whether run directly or imported by pipeline
logger = logging.getLogger("kdhe_pipeline")

# -------- Helper Functions --------

def extract_date(posted_on):
    """
    Extracts date from 'Posted on February 06, 2026 | ...'
    and converts to MM/DD/YYYY
    """
    match = re.search(r"Posted on ([A-Za-z]+ \d{2}, \d{4})", posted_on)
    if not match:
        return None
    date_str = match.group(1)
    return datetime.strptime(date_str, "%B %d, %Y").strftime("%m/%d/%Y")


def extract_city(title):
    """
    This Function attempts to extract a city or entity name from the advisory title.
    Returns (city_name_or_list, type_label) where type_label is:
    - 'structured'   → single, confidently geocodable city
    - 'unstructured' → multiple or ambiguous locations
    - 'unmatched'    → no recognizable pattern found
    """
    if not isinstance(title, str):
        return None, "unmatched"

    city_matches = re.findall(r"City of\s+([^,]+)", title, re.IGNORECASE)
    county_matches = re.findall(r"([A-Za-z\s]+County)", title, re.IGNORECASE)

    # Priority 1: Single "City of XYZ" + single county + no ambiguous keywords
    if len(city_matches) == 1 and len(county_matches) == 1:
        city_name = city_matches[0].strip()
        if not NON_GEOCODABLE.search(city_name):
            return city_name, "structured"

    # Priority 2: Match a trigger phrase and extract what follows
    for phrase in TRIGGER_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        match = pattern.search(title)
        if match:
            remainder = title[match.end():].strip()
            segments = [s.strip() for s in remainder.split(",")]

            expanded_segments = []
            for seg in segments:
                parts = re.split(r"\s+and\s+", seg, flags=re.IGNORECASE)
                expanded_segments.extend([p.strip() for p in parts])

            cleaned_segments = []
            for seg in expanded_segments:
                cleaned = re.sub(r"\s+in\s+[\w\s]+County", "", seg, flags=re.IGNORECASE).strip()
                cleaned = re.sub(r"^and\s+", "", cleaned, flags=re.IGNORECASE).strip()
                if re.match(r"^[A-Za-z\s]+County$", cleaned, re.IGNORECASE):
                    continue
                if not cleaned:
                    continue
                cleaned_segments.append(cleaned)

            if len(cleaned_segments) == 1 and not NON_GEOCODABLE.search(cleaned_segments[0]):
                return cleaned_segments[0], "structured"

            return cleaned_segments if len(cleaned_segments) > 1 else cleaned_segments[0], "unstructured"

    return None, "unmatched"


def extract_county(title):
    """
    This Function returns the county name from the title (e.g. 'Morris County'),
    or None if not found.
    """
    match = re.search(r"(\w+)\s+County", title)
    return f"{match.group(1)} County" if match else None


def enrich_record(item):
    """
    This Function adds derived fields to a single advisory record:
    issued_date, rescinded_date, year, city, city_type, county
    """
    title = item.get("title", "")
    posted_on = item.get("posted_on", "")

    issued_date = extract_date(posted_on) if ("Issued for" in title or "Re-issued for" in title) else None
    rescinded_date = extract_date(posted_on) if "Rescinded for" in title else None

    item["issued_date"] = issued_date
    item["rescinded_date"] = rescinded_date
    item["year"] = (
        issued_date.split("/")[2] if issued_date else
        rescinded_date.split("/")[2] if rescinded_date else
        None
    )
    item["city"], item["city_type"] = extract_city(title)
    item["county"] = extract_county(title)

    return item


def process_file(file_path):
    """
    This Function loads a JSON file, enriches each record, and saves to the output folder.
    """
    logger.info(f"Processing: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    enriched = [enrich_record(item) for item in data]

    output_path = Path(OUTPUT_FOLDER) / Path(file_path).name
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4)

    logger.info(f"Saved: {output_path}")


def get_json_files(folder):
    """
    This Function returns a list of all .json file paths in the given folder.
    """
    return [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(".json")
    ]


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    files = get_json_files(INPUT_FOLDER)
    logger.info(f"Found {len(files)} files to process.")

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_file, files)

    logger.info("All files processed.")


# -------- Entry Point --------

if __name__ == "__main__":

    # Retrieve the logger 
    setup_logger()
    main()