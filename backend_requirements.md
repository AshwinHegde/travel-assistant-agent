# Backend Requirements

## 1. Overview

The backend for the Travel Assistant Agent serves as the central orchestration system that:
1. Processes natural language requests
2. Extracts intent and parameters
3. Executes parallel web scraping tasks via Nova Act
4. Aggregates and scores results
5. Maintains session state
6. Provides API endpoints for frontend communication

## 2. Technical Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| Language | Python 3.10+ | Modern Python with support for type hints |
| Web Framework | FastAPI | High-performance async API framework |
| Server | Uvicorn | ASGI server for FastAPI |
| Database | SQLite + SQLModel | Simple file-based DB with SQLAlchemy-like ORM |
| Intent Parsing | LangChain + OpenAI | LLM-based natural language understanding |
| Web Scraping | Amazon Nova Act | AI-powered browser automation for travel sites |
| Concurrency | asyncio | Asynchronous task execution |
| API Documentation | OpenAPI (Swagger) | Auto-generated from FastAPI |

## 3. Key System Components

### 3.1 Intent Parser

The intent parser uses language models rather than rule-based systems to:

- **Extract Parameters**: Parse dates, destinations, budget constraints, etc.
- **Understand Context**: Maintain context across multiple messages
- **Query Planning**: Determine which scrapers to run and in what order
- **Handle Ambiguity**: Request clarification when needed

#### Implementation:

```python
# Using LangChain with OpenAI
from langchain.chains import create_extraction_chain
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-3.5-turbo-0125")

schema = {
    "properties": {
        "destination": {"type": "string"},
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
        "budget": {"type": "number"},
        "preferences": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["destination"]
}

def extract_travel_params(user_message, conversation_history=None):
    """Extract structured travel parameters from user message"""
    extraction_chain = create_extraction_chain(schema, model)
    result = extraction_chain.run(user_message)
    return result[0] if result else {}
```

### 3.2 Nova Act Scrapers

A set of specialized workers for collecting travel data:

#### Flight Scraper:
- Search multiple flight booking sites
- Filter by date, price, airline, stops
- Extract structured data: airline, times, price, etc.

#### Hotel Scraper:
- Search across hotel aggregator sites
- Filter by location, dates, price, amenities
- Extract structured data: hotel name, price, ratings, etc.

#### Experience Scraper:
- Find activities, tours, and experiences
- Filter by location, date, category
- Extract structured data: name, duration, price, etc.

### 3.3 Orchestrator

Coordinates all system components:

- **Session Management**: Store user preferences and history
- **Task Routing**: Determine which scrapers to run based on intent
- **Parallel Execution**: Run scrapers concurrently using asyncio
- **Result Aggregation**: Combine results from different scrapers
- **Scoring Algorithm**: Rank travel options based on various criteria

### 3.4 API Endpoints

```
POST /chat
Content-Type: application/json

{
  "user_id": "unique_user_id",
  "message": "I need a 3-day trip to Seattle in mid-June with a budget of $800"
}
```

Response:
```json
{
  "message": "I've found some options for your Seattle trip in mid-June.",
  "packages": [
    {
      "package_id": "pkg_123",
      "flight": { /* flight details */ },
      "hotel": { /* hotel details */ },
      "experiences": [ /* optional activities */ ],
      "total_price": 750
    }
  ],
  "next_prompts": [
    "Would you prefer cheaper hotels with fewer amenities?",
    "Are you interested in adding a whale watching tour?"
  ]
}
```

## 4. Performance Requirements

- **Latency**: Complete end-to-end processing in <15 seconds
- **Concurrency**: Support up to 10 concurrent users
- **Resilience**: Retry scraping operations on transient failures
- **Graceful Degradation**: Fall back to simpler parsing if LLM is unavailable

## 5. Implementation Phases

### Phase 1: Core Infrastructure
- Set up FastAPI application
- Implement basic language-based intent parser
- Create database models

### Phase 2: Nova Act Integration
- Implement flight search worker
- Add orchestrator for single-scraper workflow
- Create result aggregation logic

### Phase 3: Multi-Scraper Flow
- Add hotel and experience scrapers
- Implement parallel execution
- Enhance scoring algorithm

### Phase 4: Language Understanding
- Improve context handling across conversations
- Add clarification requests for ambiguous queries
- Implement follow-up suggestions
