"""
Phase 5: This Phase merge all extracted JSON files into a single output file
for further downstream processing.
"""

import json
import logging
from pathlib import Path
from logger_config import setup_logger

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent

INPUT_FOLDER  = ROOT / "data" / "advisory_reasons_output"
OUTPUT_FOLDER = ROOT / "data" / "merged_json_output"
OUTPUT_FILE   = OUTPUT_FOLDER / "merged_output.json"

# -------- Logger --------

logger = logging.getLogger("kdhe_pipeline")

# -------- Helper Functions --------

def load_json_files(folder):
    """
    This Function returns all .json file paths in the folder, sorted for consistent ordering.
    """
    files = sorted(Path(folder).glob("*.json"))
    logger.info(f"Found {len(files)} files to merge")
    return files


def load_and_merge(files):
    """
    This Function loads each JSON file and merges all records into a single list.
    """
    merged = []

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data if isinstance(data, list) else [data]
        merged.extend(records)
        logger.info(f"Loaded {len(records):>4} records from: {file_path.name}")

    return merged


def save_merged(records, output_path):
    """
    This Function saves the merged records list to a single JSON file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved merged output to: {output_path}")


# -------- Main --------

def main():
    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - MERGE")
    logger.info("Phase 5: Merging all extracted JSON files")
    logger.info("=" * 60)

    files = load_json_files(INPUT_FOLDER)
    if not files:
        logger.error(f"No JSON files found in: {INPUT_FOLDER}")
        return

    merged = load_and_merge(files)
    save_merged(merged, OUTPUT_FILE)

    logger.info("=" * 60)
    logger.info(f"Phase 5 Complete.")
    logger.info(f"Files merged     : {len(files)}")
    logger.info(f"Total records    : {len(merged)}")
    logger.info(f"Output file      : {OUTPUT_FILE}")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    setup_logger()
    main()