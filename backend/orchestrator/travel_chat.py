#!/usr/bin/env python
"""
Travel Chat Agent

This module provides a conversational agent that can understand travel intents,
identify missing information, and ask follow-up questions to collect the necessary details.
"""

import os
import uuid
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from agentops.sdk.decorators import operation, agent
import logging

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Import query parser components (using absolute imports)
from orchestrator.query_parser import (
    TravelQueryDetails,
    FlightSearchQuery,
    parse_travel_query,
    create_flight_search_queries
)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Add logger setup at the top
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_chat")

# Models for the chat functionality
class ConversationState(BaseModel):
    """Tracks the state of the conversation with the user"""
    session_id: str = Field(..., description="Unique identifier for this conversation")
    travel_details: Optional[TravelQueryDetails] = None
    original_query: Optional[str] = None
    missing_info: List[str] = Field(default_factory=list, description="List of missing information fields")
    queries_generated: bool = False
    search_queries: List[FlightSearchQuery] = Field(default_factory=list)
    last_updated_field: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response to send back to the user"""
    message: str = Field(..., description="Message to display to the user")
    missing_info: List[str] = Field(default_factory=list)
    has_complete_details: bool = False
    search_queries: List[Dict[str, Any]] = Field(default_factory=list)
    session_id: str


# Configure the model
model = OpenAIModel('gpt-4o-mini', provider=OpenAIProvider(api_key=OPENAI_API_KEY))


# Define the chat agent class with agent decorator
@agent
class TravelChatAgent:
    def __init__(self):
        self.agent = Agent(
            model,
            deps_type=ConversationState,
            instructions="""
            You are a friendly travel assistant who helps users plan trips. Your goal is to collect all the information 
            needed to search for travel options while keeping the conversation natural and engaging.
            
            CRITICAL information you MUST collect (in order of priority):
            1. ORIGIN - Where the user is traveling from (always ask this first if not provided)
            2. SPECIFIC DESTINATION - Exact city or location, not just country or state
               (e.g., ask for "San Francisco" not just "California")
            3. TRIP LENGTH - How many days they want to stay
            4. DATES - REQUIRED - When they want to travel (must be one of these):
               - Specific dates (e.g., "June 10-15")
               - A month (e.g., "June")
               - Multiple months or range (e.g., "June-July" or "summer")
               - If they say "flexible," still ask which month(s) they're considering
            
            IMPORTANT: Do not make any date assumptions. Always ask explicitly for when they want to travel.
            If user mentions "weekend" without specifying when, ask which weekend or month they're considering.
            
            NON-CRITICAL information (only ask after critical info is collected):
            - Budget preferences
            - Activity interests
            
            QUESTION FORMAT:
            When asking for missing information, ALWAYS format your questions as a numbered list, like:
            
            1. Where will you be traveling from?
            2. Which specific city in California would you like to visit?
            3. How many days are you planning to stay?
            4. Which month(s) are you considering for your trip?
            
            When information is missing:
            - ALWAYS check for and ask about ALL critical missing information at once
            - ALWAYS start with asking about origin if it's missing
            - If both origin and specific destination are missing, ask for both together
            - Date information is required - if missing, always ask for month(s) or timeframe
            - Do not move on to non-critical information until ALL critical info is provided
            - Always use numbered lists for questions
            
            For example:
            "A weekend getaway in California sounds wonderful! To help you find the best options, I need some more information:
            
            1. Where will you be traveling from?
            2. Which specific city in California would you like to visit (like San Francisco, Los Angeles, or San Diego)?
            3. How many days are you planning to stay?
            4. Which month or months are you considering for this trip?"
            
            Always maintain a friendly, helpful tone and keep responses concise while collecting all necessary information.
            Once you have all the critical information, let the user know you're searching based on what you know.
            """
        )
    
    async def run(self, message, deps):
        return await self.agent.run(message, deps=deps)

# Initialize the agent
travel_chat_agent = TravelChatAgent().agent


@travel_chat_agent.tool
@operation
async def get_conversation_context(ctx: RunContext[ConversationState]) -> str:
    """
    Get the current context of the conversation to help the model understand
    what we know and what's missing.
    """
    state = ctx.deps
    
    if not state.travel_details:
        return "This is the beginning of the conversation. No travel details have been collected yet."
    
    known_details = []
    if state.travel_details.origin:
        known_details.append(f"Origin: {state.travel_details.origin}")
    if state.travel_details.destination:
        known_details.append(f"Destination: {state.travel_details.destination}")
    if state.travel_details.trip_length_days:
        known_details.append(f"Trip length: {state.travel_details.trip_length_days} days")
    if state.travel_details.specific_month:
        known_details.append(f"Month: {state.travel_details.specific_month}")
    if state.travel_details.earliest_start_date:
        known_details.append(f"Earliest start: {state.travel_details.earliest_start_date}")
    if state.travel_details.budget:
        known_details.append(f"Budget: ${state.travel_details.budget}")
    if state.travel_details.travelers > 1:
        known_details.append(f"Travelers: {state.travel_details.travelers}")
    
    if known_details:
        context = "Current travel details:\n" + "\n".join(known_details)
    else:
        context = "No specific travel details have been collected yet."
    
    if state.missing_info:
        # Group missing information by category for better context
        missing_categories = {
            "location": ["origin", "destination"],
            "timing": ["trip_length_days", "travel_dates", "specific_month"],
            "preferences": ["budget", "travelers"]
        }
        
        grouped_missing = {}
        for category, fields in missing_categories.items():
            missing_in_category = [field for field in fields if field in state.missing_info]
            if missing_in_category:
                grouped_missing[category] = missing_in_category
        
        context += "\n\nMissing information by category:"
        for category, fields in grouped_missing.items():
            context += f"\n- {category.capitalize()}: {', '.join(fields)}"
    
    if state.last_updated_field:
        context += f"\n\nLast updated field: {state.last_updated_field}"
    
    # Add hints for multi-field responses
    context += "\n\nHINT: You should ask for ALL missing essential information at once in a natural, conversational way."
    
    return context


@travel_chat_agent.tool
@operation
async def identify_missing_information(ctx: RunContext[ConversationState]) -> str:
    """
    Check what information is still missing from the travel query.
    Distinguishes between critical and non-critical missing information.
    """
    state = ctx.deps
    
    if not state.travel_details:
        return "No travel details extracted yet."
    
    # Categorize missing information
    critical_missing = []
    nice_to_have_missing = []
    
    for field in state.missing_info:
        # Critical fields: destination, some form of dates, trip length
        if field == "destination":
            critical_missing.append(field)
        elif field == "travel_dates" and not (state.travel_details.specific_month or state.travel_details.earliest_start_date):
            critical_missing.append(field)
        elif field == "trip_length_days":
            critical_missing.append(field)
        else:
            # Non-critical fields: origin (can default), specific dates (can use month), budget, etc.
            nice_to_have_missing.append(field)
    
    result = ""
    if critical_missing:
        result += f"Critical missing information: {', '.join(critical_missing)}\n"
    
    if nice_to_have_missing:
        result += f"Additional helpful information: {', '.join(nice_to_have_missing)}\n"
    
    if not critical_missing and not nice_to_have_missing:
        result = "All essential information has been collected."
    
    # Add a note about proceeding with search
    if critical_missing:
        result += "Need this information before proceeding with search."
    elif nice_to_have_missing:
        result += "Can proceed with search, but more details would improve results."
    
    return result


@travel_chat_agent.tool
@operation
async def generate_search_queries(ctx: RunContext[ConversationState]) -> str:
    """
    Generate flight search queries once we have all the necessary information.
    """
    state = ctx.deps
    
    # First check if we have the minimum required information
    if not state.travel_details:
        return "No travel details available yet."
    
    missing = await identify_missing_information(ctx)
    if "Still missing:" in missing:
        return missing
    
    # Generate search queries
    try:
        # Make sure we have an origin before generating queries
        if not state.travel_details.origin:
            state.travel_details.origin = "current location"  # Default placeholder
        
        # Generate the queries
        state.search_queries = await create_flight_search_queries(state.travel_details)
        state.queries_generated = True
        
        if state.search_queries:
            return f"Successfully generated {len(state.search_queries)} flight search options based on your preferences."
        else:
            return "Unable to generate search queries with the current information."
    
    except Exception as e:
        return f"Error generating search queries: {str(e)}"


# Simple in-memory session storage
# In a production app, this would be a database or Redis cache
SESSION_STORAGE = {}

@operation
async def process_message(user_message: str, session_id: Optional[str] = None) -> ChatResponse:
    """
    Process a user message and update the conversation state.
    
    Args:
        user_message: The message from the user
        session_id: Optional session ID for continuing a conversation
        
    Returns:
        ChatResponse object with the assistant's reply and state information
    """
    # Get or create the conversation state
    if session_id and session_id in SESSION_STORAGE:
        # This is a continuing conversation - retrieve the state from storage
        state = SESSION_STORAGE[session_id]
    else:
        # New conversation
        session_id = session_id or str(uuid.uuid4())
        state = ConversationState(session_id=session_id)
    
    # Build full chat context for the parser
    chat_context = ""
    if state.conversation_history:
        for msg in state.conversation_history:
            chat_context += f"{msg['role'].capitalize()}: {msg['content']}\n"
    chat_context += f"User: {user_message}\n"

    # Use chat_context instead of just user_message for parsing
    if not state.travel_details:
        try:
            state.original_query = user_message
            parse_result = await parse_travel_query(chat_context)
            state.travel_details = parse_result.details
            state.missing_info = parse_result.missing_info
            if not state.missing_info:
                state.search_queries = parse_result.search_queries
                state.queries_generated = True
        except Exception as e:
            state.travel_details = TravelQueryDetails(destination="")
            state.missing_info = ["destination", "trip_length_days", "travel_dates", "origin", "budget"]
            print(f"Error parsing initial query: {str(e)}")
    else:
        try:
            parse_result = await parse_travel_query(chat_context)
            # Always trust the parser's missing_info and details
            state.travel_details = parse_result.details
            state.missing_info = parse_result.missing_info
            # Only update queries if all info is present
            if not state.missing_info:
                state.search_queries = parse_result.search_queries
                state.queries_generated = True
        except Exception as e:
            print(f"Error extracting information from follow-up message: {str(e)}")
            # If parsing fails, we'll rely on the chat agent to handle it
    
    # Update conversation history
    if not state.conversation_history:
        state.conversation_history = []
    state.conversation_history.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Create context string based on current state
    context_prefix = ""
    if state.travel_details:
        # Build a summary of what we know
        details = []
        if state.travel_details.origin:
            details.append(f"Origin: {state.travel_details.origin}")
        if state.travel_details.destination:
            details.append(f"Destination: {', '.join(state.travel_details.destination)}")
        if state.travel_details.trip_length_days:
            details.append(f"Trip length: {state.travel_details.trip_length_days} days")
        if state.travel_details.specific_month:
            details.append(f"Month: {state.travel_details.specific_month}")
        if state.travel_details.earliest_start_date:
            details.append(f"Earliest start date: {state.travel_details.earliest_start_date}")
        if state.travel_details.budget:
            details.append(f"Budget: ${state.travel_details.budget}")
        
        # Add state information to context
        context_prefix = "SYSTEM: "
        if details:
            context_prefix += f"Current travel details: {', '.join(details)}. "
        
        if state.missing_info:
            context_prefix += f"CRITICAL MISSING INFORMATION: {', '.join(state.missing_info)}. "
            
            # Emphasize origin if it's missing
            if "Origin city or airport" in state.missing_info or any("origin" in item.lower() for item in state.missing_info):
                context_prefix += "ORIGIN IS MISSING - YOU MUST ASK FOR ORIGIN FIRST. "
            
            context_prefix += "You MUST ask for ALL this missing information before proceeding. "
            context_prefix += "FORMAT YOUR QUESTIONS AS A NUMBERED LIST."
        else:
            context_prefix += "All necessary information has been collected. DO NOT ask for any more travel details. "
            context_prefix += "Instead, confirm the trip details and proceed with the search."
        
        context_prefix += "\n\n"
    
    # Process the message with the chat agent, including the context prefix
    logger.info(f"Sending to chat agent with context: {context_prefix}")
    result = await travel_chat_agent.run(context_prefix + user_message, deps=state)
    
    # Update conversation history with assistant's response
    state.conversation_history.append({
        "role": "assistant",
        "content": result.output,
        "timestamp": datetime.now().isoformat()
    })
    
    # Simplified logic: Only use parser's missing_info to determine if we can proceed
    should_generate_queries = not state.missing_info and not state.queries_generated
    
    # If we have all the information and haven't generated queries yet, do so
    if should_generate_queries:
        try:
            logger.info(f"All information collected (missing_info is empty). Generating search queries.")
            state.search_queries = await create_flight_search_queries(state.travel_details)
            state.queries_generated = True
            logger.info(f"Generated {len(state.search_queries)} search queries.")
        except Exception as e:
            logger.error(f"Error generating search queries: {str(e)}")
    
    # Save the updated state
    SESSION_STORAGE[state.session_id] = state
    
    # Create the response
    has_complete_details = not state.missing_info and state.queries_generated
    logger.info(f"Preparing response: has_complete_details={has_complete_details}, missing_info={state.missing_info}, queries_generated={state.queries_generated}")

    response = ChatResponse(
        message=result.output,
        missing_info=state.missing_info,
        has_complete_details=has_complete_details,
        session_id=state.session_id
    )

    # Only add search queries if has_complete_details is true
    if has_complete_details and state.search_queries:
        response.search_queries = [
            {
                "origin": q.origin,
                "destination": q.destination,
                "depart_date": q.depart_date.isoformat(),
                "return_date": q.return_date.isoformat(),
                "budget": q.budget,
                "travelers": q.travelers
            }
            for q in state.search_queries[:5]  # Limit to first 5 queries for brevity
        ]
        logger.info(f"Attaching {len(response.search_queries)} search queries to response.")
    else:
        response.search_queries = []
        logger.info("Not attaching search queries to response (conversation not complete).")

    return response


# For testing the module directly
if __name__ == "__main__":
    import asyncio
    
    async def test_chat():
        # Test with a vague query
        response = await process_message("I want to go on vacation")
        print(f"Assistant: {response.message}")
        print(f"Missing info: {response.missing_info}")
        
        # Continue the conversation
        if response.missing_info and response.session_id:
            follow_up = await process_message("I'd like to go to Hawaii", response.session_id)
            print(f"Assistant: {follow_up.message}")
            print(f"Missing info: {follow_up.missing_info}")
    
    asyncio.run(test_chat())
