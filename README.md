> **Illustrative Git calendar:** January-November 2026, assigned November 6, 2026.
> Actual implementation occurred in November 2026 with AI assistance. Generated
> scenarios are committed individually for this presentation calendar; commit
> counts are not evidence of earlier work or an equivalent number of features.
> See [HISTORY.md](HISTORY.md) and [SCENARIOS.md](SCENARIOS.md).

# Tour Assistant Sandbox

An original 2026 showcase for safe tour discovery and booking intent review. It models the blueprint's assistant-as-client pattern with synthetic slots and provider outcomes. **No tour is booked, no property is reserved, and no provider is contacted.** Created in November 2026; the displayed Git calendar is illustrative.

## Run

Python 3.10+ and the standard library are sufficient. No package installation, account, model download, or external service is required.

```powershell
python server.py
```

Open http://127.0.0.1:8765. The dashboard uses a fixed synthetic logical clock. Select a current slot or request a deterministic suggestion, inspect the proposal, approve it with explicit consent, then simulate an unknown or confirmed provider response. The intent and transition history are saved to a local ignored SQLite database.

An **optional**, separately running local Ollama server can suggest among current read-only options with `python server.py --model MODEL_NAME`. The model response is schema checked and cannot set consent, call booking APIs, or claim confirmation. Tests use a fake transport; no live model inference is required or claimed.

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
python cli.py options
python cli.py status REQUEST_KEY --actor demo-person --db intents.sqlite3
```

## Flow

The `status` CLI opens an existing intent database in SQLite read-only mode and never initializes its schema. Missing, unrelated, or corrupt databases exit with code 2 and a concise error rather than modifying the file. Inspection remains scoped to the supplied demo actor.

```mermaid
flowchart LR
  A[Current synthetic slot snapshots] --> B[Read-only options]
  B --> C[Deterministic or local model proposal]
  C --> D[Saved idempotent intent]
  D --> E[Explicit human consent]
  E --> F[Simulated provider result]
  F --> G[Status and audit history]
```

Latest slot versions can revoke a cached option. A proposal records the selected option but has no booking authority. Approval is scoped to the same demo actor and only transitions a proposal once. An uncertain provider result remains `RECONCILING` until an explicit later simulated outcome. The same idempotency key cannot be reused for another actor, source, or slot.

The HTTP service binds to loopback, rejects foreign Host headers and cross-origin writes, and bounds JSON requests. Actor names are demo labels, **not authentication**; this is not a production authorization boundary. Source slots, receipts, and logical times are fixtures. See [HISTORY.md](HISTORY.md) for provenance.

## Preference review and recovery

Run `python cli.py review --provider sandbox-b --max-options 2` for explained selections. `POST /api/review` accepts `{"preferences":{"provider":"sandbox-b"}}`. The result includes excluded slots and reason codes and always has proposal-only authority. `POST /api/cancel-proposal` takes a key and demo actor; it can withdraw only an owned unapproved proposal. It does not cancel anything at a real provider. Repeated identical terminal provider results are idempotent; conflicting receipts are rejected.

Run `python scenarios.py` to replay every disclosed synthetic scenario offline.
