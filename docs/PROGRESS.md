# Progress Log

Reconciled with reality on 2026-10-07 (QUEST-004). Earlier versions of this file listed every check as PENDING. Results below come from commands run on that date (Windows, Python 3.14.6 in a throwaway venv).

| Area | Status | Evidence |
|---|---|---|
| Backend (deterministic core, auth, identity challenge) | Implemented | `python -m pytest -q`: 165 passed |
| Offline scenario + safety evals | Passing | `python evals/run_evals.py`: 16/16 scenarios, 12/12 safety patterns |
| Offline adversarial suite | Passing | `python evals/run_offline_adversarial.py`: 57/57 blocked |
| Frontend type-check | Passing | `npx tsc --noEmit` exit 0 (`npm run build` not run) |
| Docker images | Not built | Dockerfiles/compose edited; `docker compose config` validates the interpolation only |
| CI | Written, never run | `.github/workflows/ci.yml`; the repo has no commits and no remote |
| Voice agent worker | Not run | Needs LiveKit + model keys; not exercised end to end |
| Browser audio | Not implemented | Dashboard has no LiveKit client |
| Outbound SIP | Not implemented | `mode=sip` returns 403/501 |
| Payments | Simulated | `backend/payments.py` is a deterministic fake |
| Live Gemini adversarial evals | Prior run only | 12/12 on 2026-10-06 before the identity/auth changes; not re-run |
| Code coverage | Not measured | The old "coverage >= 90%" gate was never run |

## Open items
- Create a git remote and see CI go green (needs the owner).
- Rotate every key that sat in `.env` (LiveKit, OpenAI, Gemini).
- Port `run_adversarial_evals.py` to drive the real HTTP API and the identity challenge, then re-run it with keys.
- Wire LiveKit dispatch and a browser audio client, or keep stating this is a simulated backend plus text harness.
