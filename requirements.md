# Travel-Agent Hackathon PoC Requirements

## 1. Overview

Build a one-day proof-of-concept “agentic” travel assistant:

* **Input**: free-form chat (e.g., “3-day Seattle trip mid-June, \$800 budget”)
* **Process**: orchestrator parses intent → fires parallel Nova Act scrapers → aggregates & scores results
* **Output**: JSON “packages” (flight + hotel \[+ experiences]) and follow-ups

> **Goal**: demonstrate
>
> 1. parallel scraping via Nova Act
> 2. minimal reruns on preference tweaks
> 3. natural-language iteration

---

## 2. Functional Requirements

### 2.1 Core Services

#### 2.1.1 Orchestrator Service

* **Run**: `poetry run uvicorn orchestrator.main:app --reload`
* **Endpoint**:

```http
POST /chat
Content-Type: application/json

{
  "user_id": "string",
  "message": "string"
}
```

* **Responsibilities**:

  1. **Intent → Task**

     * Rule-based + optional GPT-3.5 call for slot extraction
     * Produce one or more tasks, for example:

  ```json
  { "type": "search_flights", "dates": ["2025-06-14", "2025-06-17"], "budget": 800 }
  { "type": "search_hotels", "dates": ["2025-06-14", "2025-06-17"], "max_rate": 200 }
  { "type": "search_experiences", "query": "whale watching", "dates": ["2025-06-21", "2025-06-24"] }
  ```

  2. **Session State**

     * Store per-user slots (dates, budget, location, preferences) in SQLite via SQLModel
  3. **Task Routing**

     * Use `asyncio.gather()` to invoke Nova Act worker scripts in parallel
  4. **Aggregation**

     * Normalize schemas → score (weighted price/rating/distance) → combine into packages
  5. **Response**

     * Return JSON with results + “suggested next prompts”

#### 2.1.2 Nova Act Workers

* **Scripts** (in `workers/`):

  * `search_flights.py`
  * `search_hotels.py`
  * `search_experiences.py`

* **Invocation** (from Python):

  ```python
  import subprocess
  import json

  def run_worker(script: str, args: dict) -> dict:
      cmd = ["nova-act", "run", "--script", script, "--args", json.dumps(args)]
      out = subprocess.check_output(cmd)
      return json.loads(out)
  ```

* **Output**: JSON list of domain items, e.g.:

  ```json
  [
    {
      "flight_id": "XYZ123",
      "depart": "2025-06-14T08:00",
      "arrive": "2025-06-14T10:30",
      "price": 320
    },
    …
  ]
  ```

### 2.2 User Flows

1. **Initial Trip Kick-off**

   * **User**: “3-day trip to Seattle mid-June, \$800 budget”
   * **Orchestrator**: runs flights + hotels workers → returns top 3 bundles

2. **Budget/Preference Refinement**

   * **User**: “Cheaper hotels in Capitol Hill”
   * **Orchestrator**: updates `max_rate` & `neighborhood` → reruns only hotel worker → returns updated combos

3. **Date-Shift & Add Experiences**

   * **User**: “Shift to June 21–24 and add whale watching”
   * **Orchestrator**: updates dates + adds `search_experiences` → runs flights, hotels, and experiences workers → returns full itinerary

---

## 3. Non-Functional Requirements

* **Latency**: aim for <10 s end-to-end; stream intermediate “searching…” updates if possible
* **Resilience**:

  * Retry once on transient scraping errors
  * Gracefully handle CAPTCHAs/blocks with a “source unavailable” message
* **State Management**:

  * **SQLite** via SQLModel for local, file-based simplicity (no external dependencies)
  * Upgrade path: Redis for multi-user or distributed setups
* **Observability**: integrate AgentOps for end-to-end workflow monitoring, real-time task tracing, error alerts, and performance dashboards

---

## 4. Tech Stack

| Layer               | Technology                          |
| ------------------- | ----------------------------------- |
| **Language**        | Python 3.10+                        |
| **Dependency Mgmt** | Poetry                              |
| **Web Framework**   | FastAPI + Uvicorn                   |
| **Session Store**   | SQLite (local) via SQLModel         |
| **Intent Parsing**  | Regex & rule-based, optionally GPT  |
| **Parallelization** | `asyncio.gather` + Nova Act CLI     |
| **Scoring**         | Pure Python: weighted normalization |
| **Testing**         | pytest                              |

---

## 5. Poetry Setup

In `pyproject.toml`:

```toml
[tool.poetry]
name = "travel-agent-hack"
version = "0.1.0"
description = "PoC agentic travel assistant"
authors = ["You <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
fastapi = "^0.95"
uvicorn = { extras = ["standard"], version = "^0.22" }
redis = "^4.5"        # for future upgrade if needed
sqlmodel = "^0.0.8"
pydantic = "^2.0"

[tool.poetry.dev-dependencies]
pytest = "^7.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## 6. Directory Layout

```
travel-agent-hack/
├── pyproject.toml
├── README.md
├── REQUIREMENTS.md
├── orchestrator/
│   ├── main.py
│   ├── intent.py
│   ├── tasks.py
│   ├── aggregator.py
│   └── models.py
└── workers/
    ├── search_flights.py
    ├── search_hotels.py
    └── search_experiences.py
```

---

## 7. Next Steps

1. **poetry install** → set up SQLite
2. Implement `orchestrator/main.py` with `/chat` endpoint
3. Wire up one worker (e.g., flights) → test end-to-end
4. Add hotel & experience worker scripts
5. Demo the three user flows

---

This complete markdown replaces the canvas content in full.
