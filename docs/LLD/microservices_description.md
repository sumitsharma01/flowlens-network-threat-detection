> Original future architecture proposal. For the implemented local classifier and dashboard, see [ARCHITECTURE.md](../ARCHITECTURE.md). Kafka and separately deployed microservices are not part of this MVP.

# Microservices & Communication Design

## 1. Microservices

### Data Ingestion Service
- Loads UNSW-NB15 dataset or live network data.
- Outputs: raw data files or streaming events.

### Data Preprocessing Service
- Cleans, normalizes, and transforms raw network data.
- Communicates via REST or message queue to Model Service.

### Model Inference Service
- Hosts anomaly detection model (e.g., REST API).
- Receives preprocessed data, returns anomaly scores.

### API Gateway / REST API Service
- Central API for frontend and external systems.
- Routes requests to model inference service.

### Frontend Dashboard Service
- Displays results, charts, and anomalies.
- Calls API Gateway endpoints.

### Database Service
- Stores network flows, predictions, and user info.

## 2. Communication Types

### REST API
- Frontend ↔ API Gateway
- API Gateway ↔ Model Inference

### Message Queue / Event Bus (optional)
- Data Ingestion → Data Preprocessing → Model Inference

### Direct Database Writes
- Preprocessing and Model services → Database
