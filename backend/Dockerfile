FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# pytest is in requirements.txt for the test suite; harmless in the image.
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY data/customers.json /app/data/customers.json

# SQLite lives on a volume, not in the image. Non-root user owns it.
RUN useradd --create-home app && mkdir -p /app/db && chown app /app/db
ENV AUTOPAY_DB_PATH=/app/db/app.db
USER app

EXPOSE 8000

# INTERNAL_API_TOKEN and OPERATOR_API_TOKEN must be provided at runtime; there are no defaults.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
