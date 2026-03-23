FROM apache/airflow:2.11.2-python3.11

USER root
RUN chown -R airflow: /opt/airflow

USER airflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
