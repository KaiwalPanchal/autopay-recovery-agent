FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir livekit-agents livekit-plugins-openai livekit-plugins-deepgram livekit-plugins-cartesia python-dotenv httpx

COPY agent /app/agent
COPY backend /app/backend
COPY data /app/data

CMD ["python", "-m", "agent.agent", "start"]
