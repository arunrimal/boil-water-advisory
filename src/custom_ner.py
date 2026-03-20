"""
Phase 4: This Phase Custom NER - Extract Advisory Reasons from Processed Records
Uses a custom spaCy EntityRuler built from the reason dictionary to
identify advisory reasons in paragraph text.
"""

import re
import os
import json
import spacy
import logging
from pathlib import Path
from logger_config import setup_logger

# -------- Configuration --------

ROOT = Path(__file__).resolve().parent.parent

INPUT_FOLDER     = ROOT / "data" / "processed_json"
OUTPUT_FOLDER    = ROOT / "data" / "advisory_reasons_output"
DICT_PATH        = ROOT / "data" / "reference" / "reason_dictionary.json"

SPACY_MODEL      = "en_core_web_sm"

TRIGGER_PHRASES  = [
    "because of",
    "because",
    "due to",
    "caused by",
    "resulted from",
]

# -------- Logger --------

logger = logging.getLogger("kdhe_pipeline")

# -------- Helper Functions --------

def load_reason_dictionary(path):
    """
    This Function loads the reason dictionary from a JSON file.
    Returns empty dict if file not found.
    """
    if not Path(path).exists():
        logger.error(f"Reason dictionary not found at: {path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        dictionary = json.load(f)

    logger.info(f"Loaded {len(dictionary)} entries from reason dictionary")
    return dictionary


def build_nlp_pipeline(reason_dict):
    """
    This Function loads spaCy model and adds a custom EntityRuler with token-based
    patterns built from the reason dictionary.
    """
    logger.info(f"Loading spaCy model: {SPACY_MODEL}")
    nlp = spacy.load(SPACY_MODEL)

    ruler = nlp.add_pipe("entity_ruler", before="ner")

    patterns = [
        {
            "label": "ADVISORY_REASON",
            "pattern": [{"LOWER": token.lower()} for token in tokens]
        }
        for reason_phrase, tokens in reason_dict.items()
    ]

    ruler.add_patterns(patterns)
    logger.info(f"Loaded {len(patterns)} patterns into EntityRuler")

    return nlp


def extract_reason_context(paragraph, nlp):
    """
    This Function uses spaCy sentence detection to find the sentence containing a
    trigger phrase, then returns it combined with the next sentence.
    Returns the full paragraph if no trigger phrase is found.
    """
    doc = nlp(paragraph)
    sentences = list(doc.sents)

    for i, sent in enumerate(sentences):
        sent_text = sent.text.strip()
        for trigger in TRIGGER_PHRASES:
            if re.search(trigger, sent_text, re.IGNORECASE):
                next_sentence = sentences[i + 1].text.strip() if i + 1 < len(sentences) else ""
                combined = sent_text + (" " + next_sentence if next_sentence else "")
                return combined

    # No trigger found — fall back to full paragraph
    return paragraph


def extract_advisory_reasons(doc):
    """
    This Function returns all ADVISORY_REASON entities found in a spaCy doc.
    """
    return [ent.text for ent in doc.ents if ent.label_ == "ADVISORY_REASON"]


def process_advisory(advisory, nlp):
    """
    This Function processes a single advisory record — extracts reason context,
    runs NER, and returns an enriched result dictionary.
    """
    paragraph = advisory.get("paragraph", "")
    context = extract_reason_context(paragraph, nlp)
    doc = nlp(context)
    reasons = extract_advisory_reasons(doc)

    return {
        "url"                              : advisory.get("url"),
        "title"                            : advisory.get("title"),
        "combined_context"                 : context,
        "extracted_entities_advisory_reason": reasons,
        "posted_on"                        : advisory.get("posted_on"),
        "issued_date"                      : advisory.get("issued_date"),
        "rescinded_date"                   : advisory.get("rescinded_date"),
        "year"                             : advisory.get("year"),
        "city"                             : advisory.get("city"),
        "city_type"                        : advisory.get("city_type"),
        "county"                           : advisory.get("county"),
    }


def process_file(file_path, nlp, output_folder):
    """
    This Function loads a single JSON file, processes each advisory record,
    and saves enriched results to the output folder.
    """
    file_name = Path(file_path).name
    logger.info(f"Processing: {file_name}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    advisories = data if isinstance(data, list) else [data]

    results = []
    for i, advisory in enumerate(advisories):
        try:
            results.append(process_advisory(advisory, nlp))
        except Exception as e:
            logger.error(f"Error in advisory {i + 1} of {file_name}: {e}")
            continue

    output_path = output_folder / f"extracted_{file_name}"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved {len(results)} records to: {output_path}")
    return len(results)


def get_json_files(folder):
    """
    This Function returns all .json file paths in the given folder.
    """
    return list(Path(folder).glob("*.json"))


# -------- Main --------

def main():
    logger.info("=" * 60)
    logger.info("KDHE BOIL WATER ADVISORY - CUSTOM NER")
    logger.info("Phase 4: Extracting advisory reasons")
    logger.info("=" * 60)

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # Step 1: To load reason dictionary
    reason_dict = load_reason_dictionary(DICT_PATH)
    if not reason_dict:
        logger.error("Reason dictionary is empty — aborting.")
        return

    # Step 2: To build NLP pipeline once — reused across all files
    nlp = build_nlp_pipeline(reason_dict)

    # Step 3: To process all files
    json_files = get_json_files(INPUT_FOLDER)
    logger.info(f"Found {len(json_files)} files to process")

    total_advisories = 0
    for file_path in json_files:
        count = process_file(file_path, nlp, OUTPUT_FOLDER)
        total_advisories += count

    logger.info("=" * 60)
    logger.info(f"Phase 4 Complete.")
    logger.info(f"Files processed  : {len(json_files)}")
    logger.info(f"Total advisories : {total_advisories}")
    logger.info(f"Output folder    : {OUTPUT_FOLDER}")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    setup_logger()
    main()