FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend backend
COPY ml ml
COPY frontend frontend
COPY artifacts artifacts
COPY reports/evaluation.json reports/evaluation.json
COPY reports/dataset_quality.json reports/dataset_quality.json
COPY data/sample data/sample
ENV MONITOR_DB=/state/monitor.sqlite3
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
