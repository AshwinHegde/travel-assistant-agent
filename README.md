# Travel Assistant Agent

A smart agent to help plan and organize your travel experiences.

## Overview

This project provides an intelligent assistant for travel planning, offering features like:
- Trip planning and itinerary creation
- Destination recommendations
- Travel logistics assistance
- Budget tracking and management

## Setup and Installation

### Prerequisites

- Python 3.10+
- [Poetry](https://python-poetry.org/) for dependency management
- [Ollama](https://ollama.ai/) for local LLM inference
- [Nova Act](https://github.com/aws/nova-act) for web scraping

### Installation

1. Clone the repository
```bash
git clone https://github.com/AshwinHegde/travel-assistant-agent.git
cd travel-assistant-agent
```

2. Install dependencies with Poetry
```bash
cd backend
poetry install
```

3. Install and run Ollama (if not already installed)

Follow the instructions at [ollama.ai](https://ollama.ai) to install Ollama for your platform.

Then, pull the DeepSeek model which will be used by default:
```bash
ollama pull deepseek-r1:8b
```

4. Set up environment variables

Create a `.env` file in the backend directory with the following variables:
```
# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Nova Act configuration
NOVA_ACT_API_KEY=your_nova_act_api_key_here

# Ollama configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-r1:8b

# Application settings
LOG_LEVEL=INFO
DEBUG=false
```

### Running the Application

1. Start the Ollama server (if not already running)
```bash
ollama serve
```

2. Start the backend API server
```bash
cd backend
poetry run python api.py
```

3. (Optional) Test the API
```bash
curl http://localhost:8000/health
```

## Architecture

The Travel Assistant uses the following components:

- **Pydantic Models**: Type-safe data structures for all inputs and outputs
- **Ollama**: Local LLM inference for natural language understanding
- **Nova Act**: AI-powered browser automation for travel site scraping
- **FastAPI**: High-performance web API framework
- **Async Processing**: Parallel execution of search tasks

## Example Usage

```python
# Example API request
import requests
import json

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "user_id": "user123",
        "message": "I want a 3-day trip to Seattle in mid-June, budget $800.",
        "session_id": None  # For first message in conversation
    }
)

print(json.dumps(response.json(), indent=2))

# Follow-up message in same conversation
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "user_id": "user123",
        "message": "I'd prefer to stay in Capitol Hill neighborhood",
        "session_id": "session_id_from_previous_response"  # Use session_id returned from previous call
    }
)

print(json.dumps(response.json(), indent=2))
```