# Setting up AgentOps Monitoring

This guide explains how to set up AgentOps monitoring for the Travel Assistant Agent.

## Step 1: Get an AgentOps API Key

1. Sign up for an account at [AgentOps](https://agentops.ai/)
2. Create a new project for the Travel Assistant
3. Get your API key from the project settings

## Step 2: Install AgentOps SDK

```bash
# Using pip
pip install agentops

# Using poetry
poetry add agentops
```

## Step 3: Configure Environment Variables

Add your AgentOps API key to the `.env` file in the backend directory:

```
# API Settings
API_HOST=0.0.0.0
API_PORT=8000

# Monitoring and Observability
AGENTOPS_API_KEY=your_agentops_api_key_here

# Application settings
LOG_LEVEL=INFO
DEBUG=false
```

## Step 4: Initialize AgentOps in Your Code

Add the following to your application:

```python
import agentops
agentops.init(api_key="your_api_key_here")
```

## Step 5: Instrument Your Code with Decorators

```python
# Instrument key functions
from agentops.sdk.decorators import operation, agent

# Track agent operations
@agent
class MyAgent:
    # Agent implementation

# Track functions
@operation
def my_function():
    # Function implementation
```

## Step 6: Run the Application

Start the backend server as usual:

```bash
poetry run uvicorn app:app --reload
```

## Step 7: Check Monitoring Data

Once you start sending requests to the API:

1. Go to your AgentOps dashboard at [app.agentops.ai/traces](https://app.agentops.ai/traces)
2. Navigate to the "Travel Assistant" project
3. View the analytics for your application

## What Gets Tracked

With the current implementation, AgentOps will track:

1. **API Endpoints**: Performance and usage patterns of the `/chat` endpoint
2. **Agent Operations**: Activities of the TravelChatAgent
3. **Key Functions**: 
   - Processing messages
   - Conversation context retrieval
   - Missing information identification
   - Travel details updates
   - Search query generation

## Extending Monitoring

To add tracking for more components, add the appropriate decorators:

```python
# Track a function
@operation
def my_function():
    pass

# Track a class
@agent
class MyClass:
    pass

# You can add multiple decorators as needed
@agent
@operation
class MyAdvancedClass:
    pass
```

For more information, visit the [AgentOps Documentation](https://docs.agentops.ai/v2/quickstart). 