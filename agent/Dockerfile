FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-agent.txt ./
RUN pip install --no-cache-dir -r requirements-agent.txt

# agent.state imports backend.models (pydantic only). The agent never opens the database:
# it talks to the backend over HTTP with INTERNAL_API_TOKEN.
COPY agent /app/agent
COPY backend /app/backend

RUN useradd --create-home app
USER app

CMD ["python", "-m", "agent.agent", "start"]
