"""
BWA Pipeline - Airflow DAG
===========================
Project     : KDHE Boil Water Advisory (BWA) Pipeline
Author      : Arun Rimal
Email       : 
Version     : 1.0.0
Created     : 2026

Description
-----------
This DAG manages the KDHE Boil Water Advisory pipeline. It pulls
advisory notices from the KDHE website, processes and extracts
relevant information, and finally maps the affected locations
across Kansas using geocoding.

Pipeline Phases
---------------
Phase 1 - Scraping        : Collects BWA and BWO notices from the KDHE website
Phase 2 - Feature Eng.    : Cleans and prepares features from the raw data
Phase 3 - Reason Dict     : Builds a lookup dictionary of common advisory reasons
Phase 4 - Custom NER      : Identifies and extracts advisory reasons from text
Phase 5 - Merge JSON      : Combines all extracted JSON files into one dataset
Phase 6 - Geospatial Prep : Formats and prepares data for geographic analysis
Phase 7 - Geocoding       : Converts city names to coordinates and creates GeoPackage

Schedule
--------
It runs on manual trigger

"""


from datetime import datetime, timedelta
from airflow.decorators import dag, task
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scrap_advisory_notices import main as run_scraper
from src.feature_engineering import main as run_feature_engineering
from src.reason_dictionary import main as run_reason_dictionary
from src.custom_ner import main as run_custom_ner
from src.merge_json import main as run_merge_json
from src.prepare_geospatial import main as run_prepare_geospatial
from src.geocoding import main as run_geocoding


@dag(
    dag_id="bwa_pipeline",
    schedule_interval= None,   # manual trigger
    start_date=datetime(2025, 1, 1),
    catchup=False,
    default_args={
        "owner": "arun",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["bwa", "kdhe"],
)
def bwa_pipeline():

    @task()
    # Phase 1 - Scraping
    def scrape():
        run_scraper()

    @task()
    # Phase 2 - Feature Engineering
    def feature_engineering():
        run_feature_engineering()

    @task()
    # Phase 3 - Reason Dictioneary
    def reason_dictionary():
        run_reason_dictionary()

    @task()
    # Phase 4 - Custom NER
    def custom_ner():
        run_custom_ner()

    @task()
    # Phase 5 - Merge JSON
    def merge_json():
        run_merge_json()

    @task()
    # Phase 6 - Geospatial Prep
    def prepare_geospatial():
        run_prepare_geospatial()

    @task()
    # Phase 7 - Geocoding
    def geocoding():
        run_geocoding()

    # chain tasks or task dependencies
    scrape() >> feature_engineering() >> reason_dictionary() >> custom_ner() >> merge_json() >> prepare_geospatial() >> geocoding()


bwa_pipeline()