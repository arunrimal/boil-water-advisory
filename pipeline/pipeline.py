"""
BWA Pipeline - Main Entry Point
Runs all pipeline phases in order under a single shared logger.

Usage:
    python -m pipeline.main
"""

import logging
from logger_config import setup_logger
from src.scrap_advisory_notices import main as run_scraper
from src.feature_engineering import main as run_feature_engineering
from src.reason_dictionary import main as run_reason_dictionary
from src.custom_ner import main as run_custom_ner
from src.merge_json import main as run_merge_json
from src.prepare_geospatial import main as run_prepare_geospatial
from src.geocoding import main as run_geocoding



def main():

    # -------- Initialize logger ONCE here --------
    # All src/ scripts share this same logger instance via getLogger("kdhe_pipeline")
    setup_logger()
    logger = logging.getLogger("kdhe_pipeline")

    logger.info("=" * 60)
    logger.info("BWA PIPELINE STARTED")
    logger.info("=" * 60)

    # -------- Phase 1: Scraping --------
    logger.info("Starting Phase 1: Scraper")
    run_scraper()
    logger.info("Phase 1 Complete")

    # -------- Phase 2: Feature Engineering --------
    logger.info("Starting Phase 2: Feature Engineering")
    run_feature_engineering()
    logger.info("Phase 2 Complete")

    # -------- Phase 3: Building Reason Dictionary  --------
    logger.info("Starting Phase 3: Building Reason Dictionary")
    run_reason_dictionary()
    logger.info("Phase 3 Complete")

    # -------- Phase 4: Extracting Advisory Reasons - Custom NER --------
    logger.info("Starting Phase 4: Extracting Advisory Reasons - Custom NER")
    run_custom_ner()
    logger.info("Phase 4 Complete")

    # -------- Phase 5: Merging extracted JSON files  --------
    logger.info("Starting Phase 5: Merging extracted JSON files")
    run_merge_json()
    logger.info("Phase 5 Complete")

    # -------- Phase 6: Preparing Data for Geospatial Analysis  --------
    logger.info("Starting Phase 6: Preparing Data for Geospatial Analysis")
    run_prepare_geospatial()
    logger.info("Phase 6 Complete")

    
    # -------- Phase 7: Preparing for Geocoding --------
    logger.info("Starting Phase 7: Preparing for Geocoding")
    run_geocoding()
    logger.info("Phase 6 Complete")

    logger.info("=" * 60)
    logger.info("BWA PIPELINE FINISHED")
    logger.info("=" * 60)


# -------- Entry Point --------

if __name__ == "__main__":
    main()