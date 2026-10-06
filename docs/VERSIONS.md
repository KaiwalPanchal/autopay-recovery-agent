# Versions

## Python (exact pins in `requirements.txt`, verified 2026-10-07)
Installed into a clean venv on Python 3.14.6 and the full suite run against them. `pip install --dry-run --python-version 3.11` and `3.12` resolved the same pins; the suite itself was run on 3.14 only (CI will exercise 3.11 and 3.12).

| Package | Version |
|---|---|
| fastapi | 0.142.2 |
| starlette (transitive) | 1.7.0 |
| uvicorn | 0.54.0 |
| pydantic | 2.13.5 |
| sqlalchemy | 2.1.3 |
| httpx | 0.28.1 |
| python-dotenv | 1.2.4 |
| pytest | 9.1.1 |

`pyproject.toml` carries lower bounds only (`requires-python >= 3.11`).

## Voice agent (`requirements-agent.txt`)
`livekit-agents`, `livekit-plugins-openai`, `-deepgram`, `-cartesia`, `-google` all `==1.8.5`. Verified to install and import on Python 3.14 and to expose `llm.function_tool`, `AgentSession` and the `conversation_item_added` event. Not run against a live LiveKit server.

## Live evals (`requirements-live-evals.txt`)
`google-generativeai==0.8.6` (latest on PyPI at the time; the package is deprecated upstream in favour of `google-genai`).

## Frontend (`frontend/package-lock.json` is the source of truth)
Next.js 14.2.x, React 18.3.x, Tailwind 3.4.x, TypeScript 5.x. Node 20 in the Dockerfile; Node 22 on the dev machine. Not re-built in this audit.
