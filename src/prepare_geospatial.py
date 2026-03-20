"""
Phase 6: This Phase Data Preparation for Geospatial Analysis
Processes merged advisory data, matches with PWS data using exact
and fuzzy matching, and prepares the final dataset for geospatial analysis.
"""

import re
import ast
import logging
import pandas as pd
from pathlib import Path
from rapidfuzz import process, fuzz
from logger_config import setup_logger

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent

INPUT_JSON       = ROOT / "data" / "merged_json_output" / "merged_output.json"
PWS_EXCEL        = ROOT / "Data_archive" / "SDWIS 2023 KS Water System Summary.xlsx"
PWS_EXCEL_SKIPROWS = 4

OUTPUT_FOLDER    = ROOT / "data" / "geospatial_ready"

# Intermediate outputs (for debugging and inspection)
OUT_CITY_PROCESSED      = OUTPUT_FOLDER / "city_processed_combined.xlsx"
OUT_ISSUED_RESCINDED    = OUTPUT_FOLDER / "merged_issued_n_rescinded.xlsx"
OUT_FILTERED            = OUTPUT_FOLDER / "merged_issued_n_rescinded_filtered.xlsx"
OUT_CLOSEST_RESCIND     = OUTPUT_FOLDER / "merged_issued_n_rescinded_closest_rescind.xlsx"
OUT_FINAL               = OUTPUT_FOLDER / "final_for_geospatial.xlsx"

# Thresholds
RESCIND_WINDOW_DAYS  = 60    # max days between issued and rescinded to be considered a match
FUZZY_SCORE_THRESHOLD = 90   # minimum fuzzy match score (0-100) to accept a PWS match

# -------- Logger --------

logger = logging.getLogger("kdhe_pipeline")

# -------- Phase 1: City Parsing & Exploding --------

STATE_CODES = {"KS", "MO", "TX", "OK", "NE", "CO"}
BUSINESS_SUFFIXES = {"INC", "INC.", "LLC", "LLC.", "LTD", "LTD.", "CORP", "CORP.", "CO", "CO.", "MHP"}


def parse_city_field(val):
    """
    This Function parses city field into a list.
    Handles actual lists, stringified lists like "['City A', 'City B']",
    and plain strings.
    """
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val.startswith("["):
        try:
            return ast.literal_eval(val)
        except Exception:
            pass
    return [val]


def split_city_list(items):
    """
    This Function determines whether a list of city parts represents:
    - A full address (contains state code)   → join back into one string
    - A business name (contains suffix)      → join back into one string
    - Multiple separate cities               → keep as separate list items
    """
    uppercased = [str(i).strip().upper() for i in items]

    if any(item in STATE_CODES for item in uppercased):
        return [", ".join(str(i).strip() for i in items)]

    if any(item in BUSINESS_SUFFIXES for item in uppercased):
        return [", ".join(str(i).strip() for i in items)]

    return [str(i).strip() for i in items]


def process_city_column(df):
    """
    This Function splits rows with multiple cities into separate rows,
    then combines with single-city rows into one dataframe.
    """
    is_multi_city = df["city"].apply(lambda x: isinstance(x, list) and len(x) > 1)

    multi_city_df  = df[is_multi_city].copy()
    single_city_df = df[~is_multi_city].copy()

    logger.info(f"Rows with multiple cities : {len(multi_city_df)}")
    logger.info(f"Rows with single city     : {len(single_city_df)}")

    # Parse → split → explode multi-city rows
    multi_city_df["city_parsed"] = multi_city_df["city"].apply(parse_city_field)
    multi_city_df["city_parsed"] = multi_city_df["city_parsed"].apply(split_city_list)

    multi_city_exploded = (
        multi_city_df
        .explode("city_parsed")
        .drop(columns="city")
        .rename(columns={"city_parsed": "city"})
        .reset_index(drop=True)
    )

    combined = pd.concat([single_city_df, multi_city_exploded], ignore_index=True)
    logger.info(f"Total rows after exploding : {len(combined)}")

    return combined


# -------- Phase 2: City Cleaning --------

ABBREVIATIONS = {
    r"rural water district" : "rwd",
    r"mobile home park"     : "mhp",
    r"mobile home court"    : "mhc",
    r"rural water supply"   : "rws",
    r"public water supply"  : "pws",
    r"water district"       : "wd",
    r"county"               : "co",
    r"association"          : "assoc",
}

FILLERS = [
    r"a portion of the",
    r"a portion of",
    r"portions? of",
    r"located",
    r"serving",
    r"the city of",
    r"city of",
    r"town of",
]


def clean_for_matching(text):
    """
    This Function lowercases and normalizes city name for matching:
    expands abbreviations, removes fillers, strips symbols.
    """
    if pd.isna(text):
        return text

    text = str(text).lower()

    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)

    text = re.sub(r"\bno\.?\s*(?=\d)", "", text)   # rwd no. 1 → rwd 1

    for filler in FILLERS:
        text = re.sub(filler, "", text)

    text = re.sub(r"#", "", text)                   # rwd#1 → rwd1
    text = re.sub(r"\.", "", text)                  # remove periods
    text = re.sub(r"\s+", " ", text).strip()

    return text


# -------- Phase 3: Date Processing & Issued/Rescinded Merge --------

def split_issued_rescinded(df):
    """
    This Function converts date columns and splits into issued and rescinded dataframes.
    """
    df["issued_date"]    = pd.to_datetime(df["issued_date"],    errors="coerce")
    df["rescinded_date"] = pd.to_datetime(df["rescinded_date"], errors="coerce")

    issued_df    = df[df["issued_date"].notna()].copy()
    rescinded_df = df[df["rescinded_date"].notna()].copy()

    logger.info(f"Issued rows    : {len(issued_df)}")
    logger.info(f"Rescinded rows : {len(rescinded_df)}")

    return issued_df, rescinded_df


def merge_issued_rescinded(issued_df, rescinded_df):
    """
    This Function self-joins issued and rescinded on city + county.
    Filters to keep only rescinded dates after issued dates
    and within the configured window.
    Then keeps the closest rescind per issued advisory.
    """
    # Join on city + county
    merged = issued_df.merge(
        rescinded_df,
        on=["city", "county"],
        how="left",
        suffixes=("_issued", "_rescinded")
    )
    logger.info(f"Rows after merge          : {len(merged)}")

    # Calculate duration
    merged["duration_days"] = (
        merged["rescinded_date_rescinded"] - merged["issued_date_issued"]
    ).dt.days

    # Filter: rescinded must be after issued
    merged = merged[
        merged["rescinded_date_rescinded"] > merged["issued_date_issued"]
    ]
    logger.info(f"Rows after date filter    : {len(merged)}")

    # Filter: rescinded must be within configured window
    merged = merged[merged["duration_days"] <= RESCIND_WINDOW_DAYS]
    logger.info(f"Rows after {RESCIND_WINDOW_DAYS}-day window filter : {len(merged)}")

    # Keep closest rescind per issued advisory
    closest = (
        merged
        .sort_values("rescinded_date_rescinded")
        .groupby(["url_issued", "city", "county"], as_index=False)
        .first()
    )
    logger.info(f"Rows after keeping closest rescind : {len(closest)}")

    return merged, closest


ISSUED_RESCINDED_COLS = [
    "url_issued", "city", "county", "title_issued",
    "combined_context_issued",
    "extracted_entities_advisory_reason_issued",
    "posted_on_issued", "issued_date_issued",
    "year_issued", "city_cleaned_issued",
    "url_rescinded", "rescinded_date_rescinded",
    "year_rescinded", "duration_days",
]


# -------- Phase 4: PWS Data Loading & Normalization --------

PWS_NORMALIZATIONS = {
    r"\bassociation\b" : "assn",
    r"\bassn\b"        : "assn",
    r"\bdistrict\b"    : "dist",
    r"\bcompany\b"     : "co",
    r"\bcounty\b"      : "co",
    r"\bmhc\b"         : "mobile home court",
    r"\bmhp\b"         : "mobile home park",
    r"\brwd\b"         : "rural water district",
}


def normalize_name(text):
    """
    This Function normalizes a PWS or city name for consistent matching.
    """
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", " ", text).strip()

    for pattern, replacement in PWS_NORMALIZATIONS.items():
        text = re.sub(pattern, replacement, text)

    return text


def load_pws_data(path, skiprows):
    """
    This Function loads and normalizes the PWS reference Excel file.
    """
    logger.info(f"Loading PWS data from: {path}")
    pws_df = pd.read_excel(path, skiprows=skiprows)

    pws_df["PWS_clean"] = (
        pws_df["PWS Name"]
        .str.split(",", n=1)
        .str[0]
        .str.strip()
        .str.lower()
    )
    pws_df["pws_norm"] = pws_df["PWS_clean"].astype(str).apply(normalize_name)

    logger.info(f"Loaded {len(pws_df)} PWS records")
    return pws_df


# -------- Phase 5: Exact Matching --------

MATCH_COLS = [
    "url_issued", "PWS ID", "PWS_clean", "PWS Name",
    "issued_date_issued", "rescinded_date_rescinded", "Population Served Count",
    "city_cleaned_issued", "city_norm", "Cities Served", "city",
    "Counties Served", "county",
]


def exact_match(advisory_df, pws_df):
    """
    This Function merges advisory data with PWS data on normalized city name.
    """
    matches = advisory_df.merge(
        pws_df,
        left_on="city_norm",
        right_on="pws_norm",
        how="inner"
    )
    logger.info(f"Exact matches : {len(matches)}")
    return matches[MATCH_COLS]


# -------- Phase 6: Fuzzy Matching --------

def fuzzy_match(advisory_df, pws_df, matched_set):
    """
    This Function runs fuzzy matching on cities not already exact-matched.
    Filters by configured score threshold.
    """
    unmatched = (
        advisory_df["city_norm"]
        .drop_duplicates()
        .loc[lambda x: ~x.isin(matched_set)]
    )
    logger.info(f"Unmatched cities to fuzzy match : {len(unmatched)}")

    pws_names = pws_df["pws_norm"].tolist()

    results = []
    for city in unmatched:
        match, score, _ = process.extractOne(city, pws_names, scorer=fuzz.token_sort_ratio)
        results.append({"city_norm": city, "matched_pws": match, "score": score})

    fuzzy_df = pd.DataFrame(results)
    fuzzy_df = fuzzy_df[fuzzy_df["score"] >= FUZZY_SCORE_THRESHOLD]
    logger.info(f"Fuzzy matches above threshold : {len(fuzzy_df)}")

    # Join back with PWS data and advisory data
    fuzzy_full = fuzzy_df.merge(pws_df,    left_on="matched_pws", right_on="pws_norm", how="left")
    fuzzy_full = fuzzy_full.merge(advisory_df, on="city_norm", how="left")

    return fuzzy_full[MATCH_COLS]


# -------- Main --------

def main():
    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - GEOSPATIAL DATA PREPARATION")
    logger.info("Phase 6: Preparing data for geospatial analysis")
    logger.info("=" * 60)

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

    # --- Phase 1: To load and process city column ---
    logger.info("Phase 6.1: Loading merged JSON and processing city column")
    df = pd.read_json(INPUT_JSON)
    df = process_city_column(df)
    df.to_excel(OUT_CITY_PROCESSED, index=False)
    logger.info(f"Saved: {OUT_CITY_PROCESSED}")

    # --- Phase 2: To clean city names ---
    logger.info("Phase 6.2: Cleaning city names for matching")
    df["city_cleaned"] = df["city"].apply(clean_for_matching)

    # --- Phase 3: To date processing and issued/rescinded merge ---
    logger.info("Phase 6.3: Splitting issued and rescinded records")
    issued_df, rescinded_df = split_issued_rescinded(df)

    # issued_df["city_cleaned_issued"] = issued_df["city_cleaned"]

    logger.info("Phase 6.3: Merging issued and rescinded records")
    merged, closest = merge_issued_rescinded(issued_df, rescinded_df)

    merged.to_excel(OUT_ISSUED_RESCINDED, index=False)
    logger.info(f"Saved: {OUT_ISSUED_RESCINDED}")

    closest_selected = closest[ISSUED_RESCINDED_COLS]
    closest_selected.to_excel(OUT_CLOSEST_RESCIND, index=False)
    logger.info(f"Saved: {OUT_CLOSEST_RESCIND}")

    # --- Phase 4: To Load and normalize PWS data ---
    logger.info("Phase 6.4: Loading PWS reference data")
    pws_df = load_pws_data(PWS_EXCEL, PWS_EXCEL_SKIPROWS)

    # --- Phase 5 & 6: To Normalize, exact match, fuzzy match ---
    logger.info("Phase 6.5: Normalizing city names and running exact match")
    closest_selected = closest_selected.copy()
    closest_selected["city_norm"] = closest_selected["city_cleaned_issued"].astype(str).apply(normalize_name)

    exact_matches = exact_match(closest_selected, pws_df)
    matched_set   = set(exact_matches["city_norm"])

    logger.info("Phase 6.6: Running fuzzy match on unmatched cities")
    fuzzy_matches = fuzzy_match(closest_selected, pws_df, matched_set)

    # --- Combine and save final output ---
    logger.info("Phase 6.7: Combining exact and fuzzy matches")
    final = pd.concat([exact_matches, fuzzy_matches], ignore_index=True)
    final.to_excel(OUT_FINAL, index=False)
    logger.info(f"Saved: {OUT_FINAL}")

    logger.info("=" * 60)
    logger.info("Phase 6 Complete.")
    logger.info(f"Exact matches  : {len(exact_matches)}")
    logger.info(f"Fuzzy matches  : {len(fuzzy_matches)}")
    logger.info(f"Final records  : {len(final)}")
    logger.info(f"Output folder  : {OUTPUT_FOLDER}")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    setup_logger()
    main()