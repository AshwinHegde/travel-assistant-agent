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

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Import query parser components
from .query_parser import (
    TravelQueryDetails,
    FlightSearchQuery,
    parse_travel_query,
    create_flight_search_queries,
    generate_date_options
)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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


# Define the chat agent
travel_chat_agent = Agent(
    model,
    deps_type=ConversationState,
    instructions="""
    You are a friendly travel assistant who helps users plan trips. Your goal is to collect all the information 
    needed to search for travel options while keeping the conversation natural and engaging.
    
    When information is missing:
    - Ask ONE question at a time in a conversational way
    - Focus on the most important missing detail first
    - Use what you already know about the user's preferences
    - Offer reasonable suggestions when appropriate
    - Be empathetic and understanding
    
    For example, instead of "Please provide your destination", say something like 
    "That sounds like a fun trip! Where were you thinking of traveling to?"
    
    Always maintain a friendly, helpful tone and keep responses concise.
    """
)


@travel_chat_agent.tool
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
        context += f"\n\nMissing information: {', '.join(state.missing_info)}"
    
    if state.last_updated_field:
        context += f"\n\nLast updated field: {state.last_updated_field}"
    
    return context


@travel_chat_agent.tool
async def identify_missing_information(ctx: RunContext[ConversationState]) -> str:
    """
    Check what information is still missing from the travel query.
    This uses the missing_info list that was originally populated by the query parser.
    """
    state = ctx.deps
    
    if not state.travel_details:
        return "No travel details extracted yet."
    
    # The missing_info list should already be populated from the query parser
    # or updated when fields are changed
    
    if state.missing_info:
        return f"Still missing: {', '.join(state.missing_info)}"
    else:
        return "All essential information has been collected."


@travel_chat_agent.tool
async def update_travel_details(
    ctx: RunContext[ConversationState], 
    field: str, 
    value: str
) -> str:
    """
    Update the travel details based on user response.
    """
    state = ctx.deps
    
    # Initialize travel details if not already done
    if not state.travel_details:
        state.travel_details = TravelQueryDetails(destination="")
    
    # Update the appropriate field based on user input
    if field == "destination":
        state.travel_details.destination = value
    
    elif field == "origin":
        state.travel_details.origin = value
    
    elif field == "trip_length_days":
        try:
            # Handle conversational responses
            value = value.lower()
            if "week" in value:
                days = 7
                if "one" in value or "1" in value:
                    days = 7
                elif "two" in value or "2" in value:
                    days = 14
                state.travel_details.trip_length_days = days
            else:
                # Try to extract a number
                import re
                number_match = re.search(r'\d+', value)
                if number_match:
                    days = int(number_match.group())
                    state.travel_details.trip_length_days = days
                else:
                    return f"Could not determine the trip length from '{value}'."
        except:
            return f"Could not parse '{value}' as a trip length."
    
    elif field == "specific_month":
        # Clean up month name and standardize it
        months = ["january", "february", "march", "april", "may", "june", 
                  "july", "august", "september", "october", "november", "december"]
        
        cleaned_value = value.lower().strip()
        # Handle abbreviations
        for i, month in enumerate(months):
            if month.startswith(cleaned_value) or month[:3] == cleaned_value.lower():
                cleaned_value = month
                break
        
        # Set month if it's valid
        if cleaned_value in months:
            state.travel_details.specific_month = cleaned_value.capitalize()
        else:
            return f"'{value}' doesn't seem to be a valid month."
    
    elif field == "travel_dates":
        # Try to parse as a month name first
        months = ["january", "february", "march", "april", "may", "june", 
                  "july", "august", "september", "october", "november", "december"]
        
        value_lower = value.lower()
        for month in months:
            if month in value_lower or month[:3] in value_lower:
                state.travel_details.specific_month = month.capitalize()
                return f"Set travel month to {month.capitalize()}"
        
        # Otherwise try to extract date ranges
        try:
            import re
            # This is a simplistic approach - would need more robust parsing in production
            if "to" in value or "-" in value:
                parts = re.split(r'\s+to\s+|-', value)
                if len(parts) == 2:
                    # Very basic parsing - would need proper date parsing in a real app
                    return f"Detected date range in '{value}', but would need more specific formatting."
            
            return f"Could not parse '{value}' as travel dates. Please specify a month or date range."
        except:
            return f"Could not parse '{value}' as travel dates."
    
    elif field == "budget":
        try:
            # Remove currency symbols and commas
            cleaned_value = value.replace('$', '').replace(',', '').strip()
            # Extract the number
            import re
            match = re.search(r'\d+', cleaned_value)
            if match:
                budget = float(match.group())
                state.travel_details.budget = budget
            else:
                return f"Could not extract a budget amount from '{value}'."
        except:
            return f"Could not parse '{value}' as a budget amount."
    
    elif field == "travelers":
        try:
            # Handle conversational responses
            value_lower = value.lower()
            if "alone" in value_lower or "just me" in value_lower or "myself" in value_lower:
                state.travel_details.travelers = 1
            elif "couple" in value_lower or "two" in value_lower or "2" in value:
                state.travel_details.travelers = 2
            elif "family" in value_lower:
                # Assume a typical family of 4 if not specified
                state.travel_details.travelers = 4
            else:
                # Try to extract a number
                import re
                number_match = re.search(r'\d+', value)
                if number_match:
                    travelers = int(number_match.group())
                    state.travel_details.travelers = travelers
                else:
                    return f"Could not determine the number of travelers from '{value}'."
        except:
            return f"Could not parse '{value}' as a number of travelers."
    
    # Update the state
    state.last_updated_field = field
    
    # Check if this field was in missing_info and remove it
    if field in state.missing_info:
        state.missing_info.remove(field)
    elif field == "travel_dates" and "travel_dates" in state.missing_info:
        state.missing_info.remove("travel_dates")
    
    return f"Updated {field} to {value}"


@travel_chat_agent.tool
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
        state.search_queries = create_flight_search_queries(state.travel_details)
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
    
    # If this is a new conversation, try to parse initial travel intent
    if not state.travel_details:
        try:
            # Record the original query
            state.original_query = user_message
            
            # Parse the query
            parse_result = await parse_travel_query(user_message)
            
            # Use the details and missing_info directly from the parser
            state.travel_details = parse_result.details
            state.missing_info = parse_result.missing_info
            
            # If we already have enough details, generate search queries
            if not parse_result.missing_info:
                state.search_queries = parse_result.search_queries
                state.queries_generated = True
        except Exception as e:
            # If parsing fails, just initialize with an empty travel details object
            state.travel_details = TravelQueryDetails(destination="")
            # Set standard missing fields
            state.missing_info = ["destination", "trip_length_days", "travel_dates", "origin", "budget"]
            print(f"Error parsing initial query: {str(e)}")
    
    # Update conversation history
    if not state.conversation_history:
        state.conversation_history = []
    state.conversation_history.append({
        "role": "user",
        "content": user_message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Process the message with the chat agent
    result = await travel_chat_agent.run(user_message, deps=state)
    
    # Update conversation history with assistant's response
    state.conversation_history.append({
        "role": "assistant",
        "content": result.output,
        "timestamp": datetime.now().isoformat()
    })
    
    # Save the updated state
    SESSION_STORAGE[state.session_id] = state
    
    # Create the response
    response = ChatResponse(
        message=result.output,
        missing_info=state.missing_info,
        has_complete_details=not state.missing_info and state.queries_generated,
        session_id=state.session_id
    )
    
    # Add search queries if they've been generated
    if state.queries_generated and state.search_queries:
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