"""
Phase 3: This Phase Build Reason Dictionary
Extracts unique advisory reasons from Excel backup(from old datasets available), merges with existing
dictionary, sorts by longest key first, and saves to reference folder.
"""


import re
import json
import logging
import pandas as pd
from os import mkdir
from pathlib import Path
from logger_config import setup_logger

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent

(ROOT / "data" / "reference").mkdir(parents=True, exist_ok=True)
(ROOT / "data" / "reference" /"reference_backup").mkdir(parents=True, exist_ok=True)

EXCEL_PATH        = ROOT / "Data_archive" / "BWA_KS.xlsx"
BACKUP_DICT_PATH  = ROOT / "data" / "reference" /"reference_backup" / "reason_dictionary_backup.json"
OUTPUT_PATH       = ROOT / "data" / "reference" / "reason_dictionary.json"

EXCEL_REASON_COLUMN = "Reason"

# -------- Logger --------

logger = logging.getLogger("kdhe_pipeline")

# -------- Helper Functions --------

def clean_reason(text):
    """
    This Function lowercases, strips, removes punctuation, and collapses extra whitespace.
    """
    text = text.lower()
    text = text.strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def load_excel_reasons(excel_path, column):
    """
    This Function reads the Excel file and returns a list of cleaned unique reasons
    from the specified column.
    """
    logger.info(f"Loading Excel file: {excel_path}")
    df = pd.read_excel(excel_path)

    if column not in df.columns:
        logger.error(f"Column '{column}' not found in Excel file. Available columns: {list(df.columns)}")
        return []

    raw_reasons = df[column].dropna().unique()
    cleaned = sorted(set(clean_reason(r) for r in raw_reasons))

    logger.info(f"Extracted {len(cleaned)} unique reasons from Excel")
    return cleaned


def build_dictionary(reasons):
    """
    This Function builds a reason dictionary from a list of cleaned reason strings.
    Value is the key split by whitespace.
    """
    return {reason: reason.split() for reason in reasons}


def load_backup_dictionary(path):
    """
    This Function loads the existing backup reason dictionary if it exists.
    Returns empty dict if file not found.
    """
    if not path.exists():
        logger.info("No existing backup dictionary found — starting fresh.")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        backup = json.load(f)

    logger.info(f"Loaded {len(backup)} entries from backup dictionary")
    return backup


def merge_and_sort(new_dict, backup_dict):
    """
    This zFunction unions new and backup dictionaries, then sorts by longest key first.
    Since values are always derived from keys, no conflicts are possible.
    """
    merged = {**backup_dict, **new_dict}
    sorted_dict = dict(sorted(merged.items(), key=lambda x: len(x[0]), reverse=True))

    logger.info(f"Merged dictionary contains {len(sorted_dict)} unique entries")
    return sorted_dict


def save_dictionary(dictionary, path):
    """
    This Functions saves the dictionary to a JSON file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=4)
    logger.info(f"Saved reason dictionary to: {path}")


# -------- Main --------

def main():
    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - REASON DICTIONARY BUILDER")
    logger.info("Phase 3: Building and updating reason dictionary")
    logger.info("=" * 60)

    # Step 1: To Extract reasons from Excel
    cleaned_reasons = load_excel_reasons(EXCEL_PATH, EXCEL_REASON_COLUMN)
    if not cleaned_reasons:
        logger.error("No reasons extracted — aborting.")
        return

    # Step 2: To build new dictionary
    new_dict = build_dictionary(cleaned_reasons)
    logger.info(f"Built new dictionary with {len(new_dict)} entries")

    # Step 3: To load existing backup dictionary
    backup_dict = load_backup_dictionary(BACKUP_DICT_PATH)

    # Step 4: To merge and sort by longest key first
    final_dict = merge_and_sort(new_dict, backup_dict)

    # Step 5: To Save
    save_dictionary(final_dict, OUTPUT_PATH)

    # Step 6: To backup current dictionary
    save_dictionary(final_dict, BACKUP_DICT_PATH)

    logger.info("=" * 60)
    logger.info("Phase 3 Complete. Reason dictionary ready.")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    setup_logger()
    main()