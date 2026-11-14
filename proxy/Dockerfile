# Measuring proxy (A4). Build context is the repo root (see docker-compose.yml).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY proxy/ proxy/
COPY pricing.yaml .
ENV PRICING_FILE=/app/pricing.yaml FAULTS_DIR=/app/faults
EXPOSE 8001
CMD ["uvicorn", "proxy.app:app", "--host", "0.0.0.0", "--port", "8001"]
