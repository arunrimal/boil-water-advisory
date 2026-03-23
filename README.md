## KDHE Boil Water Advisory (BWA) Pipeline

This pipeline project that collects and maps boil water notices published by KDHE across Kansas.

---

## Author
- **Name:** Arun Rimal
- **Email:** aarunrimal92@gmail.com

---

## Project Overview

KDHE publishes boil water notices whenever a water supply in Kansas may be 
contaminated. This pipeline collects those notices, extracts the reasons behind 
them, and maps the address to a geometry(geocoding) and later geocoded dataset is used to map the affected locations across the state.

## How the pipeline works

The pipeline runs in 7 steps, each handled by a separate script:

| Step | Script | What it does |
|------|--------|--------------|
| 1 | `scrap_advisory_notices.py` | Pulls notices from the KDHE website |
| 2 | `feature_engineering.py` | Cleans up the raw data and builds useful features |
| 3 | `reason_dictionary.py` | Creates a reference list of common advisory reasons |
| 4 | `custom_ner.py` | Reads through the notice text and tags the reasons |
| 5 | `merge_json.py` | Brings all the extracted pieces together |
| 6 | `prepare_geospatial.py` | Gets the data ready for mapping |
| 7 | `geocoding.py` | Looks up coordinates for each location and saves the map file |

---

## Project structure
```
project_root/
├── dags/
│   └── bwa_dag.py            
├── src/
│   ├── scrap_advisory_notices.py
│   ├── feature_engineering.py
│   ├── reason_dictionary.py
│   ├── custom_ner.py
│   ├── merge_json.py
│   ├── prepare_geospatial.py
│   └── geocoding.py
├── data/
│   ├── advisory_reasons_output/   
|   ├── extracted_json/ 
|   ├── geocoded_output/ 
|   ├── geospatial_ready/
|   ├── merged_json_output/         
│   └── processed_json/            
│         
├── logs/                     
├── Dockerfile                
├── docker-compose.yaml       
├── requirements.txt          
├── pipeline/
│   └── pipeline.py               
├── logger_config.py          
└── README.md
```

---

## Tools used

- **Python 3.11**
- **Apache Airflow 2.11.2** for scheduling and monitoring the pipeline
- **Docker** so the whole thing runs the same way on any machine
- **spaCy** for reading and tagging advisory text
- **GeoPandas** for working with geographic data
- **Nominatim (OpenStreetMap)** for looking up coordinates
- **PostgreSQL** as the backend database for Airflow

---

## Getting it running

You'll need Docker Desktop installed before you start.

**1 — Clone the repo and go into the folder:**
```bash
git clone 
cd "Capston Project - Boil Water Advisory"
```

**2 — Build the image:**
```bash
docker compose build
```

**3 — Set up the database:**
```bash
docker compose up airflow-init
```

**4 — Start everything:**
```bash
docker compose up -d
```

**5 — Create a login:**
```bash
docker compose exec airflow-webserver airflow users create \
    --username admin \
    --password admin \
    --firstname arun(eg.) \
    --lastname rimal(eg.) \
    --role Admin \
    --email ...
```

**6 — Open the Airflow UI:**
```
http://localhost:8080
```

---

## Running the pipeline

The pipeline does not run on a schedule — you trigger it manually when needed.
Just open the Airflow UI, find `bwa_pipeline`, and hit the play button.

---

## Data sources

- KDHE Disruption in Water Service: https://www.kdhe.ks.gov/468/Disruption-in-Water-Service
- Boil Water Bulletin: https://www.kdhe.ks.gov/CivicAlerts.aspx?CID=29
- Consumer Confidence Reports: https://www.kdhe.ks.gov/531/Consumer-Confidence-Reports

---

## A few things to keep in mind

The geocoding step uses Nominatim which is a free service with a limit of one 
request per second, so it takes a few minutes to get through all 270(eg.) records. 
Consumer Confidence Reports used in this project cover the years 2019 to 2025. 
If you want to run the pipeline without Airflow, you can use `pipeline.py` directly.


## Running without Airflow

Navigate to the project root directory and run:

python -m pipeline.pipeline
