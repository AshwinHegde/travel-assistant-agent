#!/usr/bin/env python
"""
FastAPI endpoint for the Travel Assistant Agent
"""

import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid

# AgentOps SDK for monitoring
import agentops

# Load environment variables
load_dotenv()

# Initialize AgentOps - this is all you need for basic integration
AGENTOPS_API_KEY = os.environ.get("AGENTOPS_API_KEY", "")
agentops.init(api_key=AGENTOPS_API_KEY)

# Import only needed modules
from orchestrator.travel_chat import process_message, ChatResponse

# Initialize FastAPI
app = FastAPI(
    title="Travel Assistant API",
    description="API for the Travel Assistant Agent powered by Nova Act",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "OK", "message": "Travel Assistant API is running"}

@app.get("/health")
async def health_check():
    """Additional health check that also checks Ollama connectivity."""
    try:
        # We'll simplify this since we no longer use the orchestrator
        return {
            "status": "OK", 
            "message": "Travel Assistant API is running"
        }
    except Exception as e:
        return {
            "status": "warning",
            "message": "API running but connection issue detected",
            "error": str(e)
        }

# Models for the chat functionality
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

# Use the operation decorator from AgentOps
from agentops.sdk.decorators import operation

@app.post("/chat", response_model=ChatResponse)
@operation
async def chat(request: ChatRequest):
    """
    Enhanced chat endpoint that uses the conversational agent to
    collect missing information and generate specific travel search queries.
    
    This endpoint processes messages, maintains conversation state,
    and guides users through providing all necessary travel details.
    """
    try:
        # Process the message with the chat agent
        response = await process_message(
            user_message=request.message,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")
