# Backend - Travel Assistant Agent

This directory contains the server-side code for the Travel Assistant Agent.

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI with Uvicorn
- **Database**: SQLite via SQLModel
- **Intent Parsing**: Language-based (OpenAI/LangChain) with fallback to regex patterns
- **Scraping**: Amazon Nova Act for browser automation
- **Parallelization**: asyncio for concurrent scraping tasks

## Key Components

### Intent Parser

The intent parser uses language models (via OpenAI/LangChain) to:
1. Extract structured travel information (dates, locations, budget, preferences)
2. Generate a query plan that determines which scrapers to run
3. Handle complex natural language queries with context

This approach is more powerful than regex/rule-based parsing, allowing for:
- Natural language understanding of ambiguous requests
- Context-aware responses
- Progressive refinement of travel plans

### Nova Act Workers

These workers handle the actual web scraping tasks:
- `search_flights.py`: Searches for flight options on travel sites
- `search_hotels.py`: Finds hotel accommodations matching criteria
- `search_experiences.py`: Discovers activities and tours

### Orchestrator

The orchestrator coordinates the entire workflow:
- Manages user sessions and state
- Routes tasks to appropriate workers
- Runs tasks in parallel using asyncio
- Aggregates and scores results
- Generates responses with suggested follow-ups

## Setup

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
cd backend
poetry install

# Create database
poetry run python -c "from orchestrator.models import create_db_and_tables; create_db_and_tables()"

# Run the service
poetry run uvicorn orchestrator.main:app --reload
```

## API Documentation

API endpoints will be documented here as they are developed. 