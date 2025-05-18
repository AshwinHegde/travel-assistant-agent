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

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Import query parser components
# Use absolute import path instead of relative import
from orchestrator.query_parser import (
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
            
            When information is missing:
            - Ask for ALL missing essential details in a single conversational message
            - Frame your questions in a natural, friendly way that flows like a normal conversation
            - Group related questions together (like dates and duration)
            - Use what you already know about the user's preferences to personalize questions
            - Offer reasonable suggestions or options when appropriate
            - Be empathetic and understanding
            
            For example, instead of a checklist of questions, say something like:
            "That sounds like a fun trip to New York! To help you find the best options, could you tell me when you're 
            planning to travel and how long you'd like to stay? Also, are you traveling from your home in Seattle, and 
            do you have a budget in mind for this trip?"
            
            Always maintain a friendly, helpful tone and keep responses concise while collecting all necessary information.
            Once you have all the required information, let the user know you're ready to search for options.
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
@operation
async def update_travel_details(
    ctx: RunContext[ConversationState], 
    field: str, 
    value: str
) -> str:
    """
    Update the travel details based on user response using the query parser.
    This leverages the existing parsing logic instead of duplicating it.
    """
    state = ctx.deps
    
    # Initialize travel details if not already done
    if not state.travel_details:
        state.travel_details = TravelQueryDetails(destination="")
    
    # Construct a query that focuses on the specific field
    field_queries = {
        "destination": f"I want to go to {value}",
        "origin": f"I want to travel from {value}",
        "trip_length_days": f"I want to travel for {value} days",
        "specific_month": f"I want to travel in {value}",
        "travel_dates": f"I want to travel on {value}",
        "budget": f"My budget is {value}",
        "travelers": f"There will be {value} travelers"
    }
    
    query = field_queries.get(field, f"My {field} is {value}")
    
    try:
        # Parse the field-specific query
        parse_result = await parse_travel_query(query)
        
        # Update only the specific field from the parse result, keep other fields as is
        updated = False
        
        if field == "destination" and parse_result.details.destination:
            state.travel_details.destination = parse_result.details.destination
            updated = True
        
        elif field == "origin" and parse_result.details.origin:
            state.travel_details.origin = parse_result.details.origin
            updated = True
        
        elif field == "trip_length_days" and parse_result.details.trip_length_days:
            state.travel_details.trip_length_days = parse_result.details.trip_length_days
            updated = True
        
        elif field == "specific_month" and parse_result.details.specific_month:
            state.travel_details.specific_month = parse_result.details.specific_month
            updated = True
        
        elif field == "travel_dates":
            # Handle both month and specific dates
            if parse_result.details.specific_month:
                state.travel_details.specific_month = parse_result.details.specific_month
                updated = True
            if parse_result.details.earliest_start_date:
                state.travel_details.earliest_start_date = parse_result.details.earliest_start_date
                updated = True
            if parse_result.details.latest_start_date:
                state.travel_details.latest_start_date = parse_result.details.latest_start_date
                updated = True
        
        elif field == "budget" and parse_result.details.budget:
            state.travel_details.budget = parse_result.details.budget
            updated = True
        
        elif field == "travelers" and parse_result.details.travelers > 0:
            state.travel_details.travelers = parse_result.details.travelers
            updated = True
        
        # If parsing via the query parser didn't work, fall back to direct assignment for simple fields
        if not updated:
            if field == "destination":
                state.travel_details.destination = value
            elif field == "origin":
                state.travel_details.origin = value
            elif field == "specific_month":
                # Simple cleanup for month names
                months = ["january", "february", "march", "april", "may", "june", 
                          "july", "august", "september", "october", "november", "december"]
                cleaned_value = value.lower().strip()
                for month in months:
                    if month.startswith(cleaned_value) or month[:3] == cleaned_value.lower():
                        state.travel_details.specific_month = month.capitalize()
                        break
            # Add fallbacks for other fields as needed
    
    except Exception as e:
        print(f"Error using query parser for update: {str(e)}")
        # Fall back to basic parsing if query parser fails
        if field == "destination":
            state.travel_details.destination = value
        elif field == "origin":
            state.travel_details.origin = value
        # Add other basic field assignments here
    
    # Update the state
    state.last_updated_field = field
    
    # Check if this field was in missing_info and remove it
    if field in state.missing_info:
        state.missing_info.remove(field)
    elif field == "travel_dates" and "travel_dates" in state.missing_info:
        state.missing_info.remove("travel_dates")
    
    return f"Updated {field} to {value}"


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
    else:
        # This is a follow-up message, try to extract multiple pieces of information
        try:
            # Always run the query parser on follow-up messages to extract any information
            parse_result = await parse_travel_query(user_message)
            
            # Update any fields that were extracted by the parser
            updated_fields = []
            
            # Check and update destination
            if parse_result.details.destination and (
                not state.travel_details.destination or 
                parse_result.details.destination != state.travel_details.destination
            ):
                state.travel_details.destination = parse_result.details.destination
                if "destination" in state.missing_info:
                    state.missing_info.remove("destination")
                updated_fields.append("destination")
            
            # Check and update origin
            if parse_result.details.origin and (
                not state.travel_details.origin or 
                parse_result.details.origin != state.travel_details.origin
            ):
                state.travel_details.origin = parse_result.details.origin
                if "origin" in state.missing_info:
                    state.missing_info.remove("origin")
                updated_fields.append("origin")
            
            # Check and update trip length
            if parse_result.details.trip_length_days and (
                not state.travel_details.trip_length_days or 
                parse_result.details.trip_length_days != state.travel_details.trip_length_days
            ):
                state.travel_details.trip_length_days = parse_result.details.trip_length_days
                if "trip_length_days" in state.missing_info:
                    state.missing_info.remove("trip_length_days")
                updated_fields.append("trip length")
            
            # Check and update month/dates
            date_fields_updated = False
            
            if parse_result.details.specific_month and (
                not state.travel_details.specific_month or 
                parse_result.details.specific_month != state.travel_details.specific_month
            ):
                state.travel_details.specific_month = parse_result.details.specific_month
                date_fields_updated = True
                updated_fields.append("month")
            
            if parse_result.details.earliest_start_date and (
                not state.travel_details.earliest_start_date or 
                parse_result.details.earliest_start_date != state.travel_details.earliest_start_date
            ):
                state.travel_details.earliest_start_date = parse_result.details.earliest_start_date
                date_fields_updated = True
                updated_fields.append("start date")
            
            if date_fields_updated and "travel_dates" in state.missing_info:
                state.missing_info.remove("travel_dates")
            
            # Check and update budget
            if parse_result.details.budget and (
                not state.travel_details.budget or 
                parse_result.details.budget != state.travel_details.budget
            ):
                state.travel_details.budget = parse_result.details.budget
                if "budget" in state.missing_info:
                    state.missing_info.remove("budget")
                updated_fields.append("budget")
            
            # Check and update travelers
            if parse_result.details.travelers > 1 and (
                state.travel_details.travelers == 1 or 
                parse_result.details.travelers != state.travel_details.travelers
            ):
                state.travel_details.travelers = parse_result.details.travelers
                if "travelers" in state.missing_info:
                    state.missing_info.remove("travelers")
                updated_fields.append("number of travelers")
            
            if updated_fields:
                print(f"Updated fields from follow-up message: {', '.join(updated_fields)}")
        
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
    
    # Process the message with the chat agent
    result = await travel_chat_agent.run(user_message, deps=state)
    
    # Update conversation history with assistant's response
    state.conversation_history.append({
        "role": "assistant",
        "content": result.output,
        "timestamp": datetime.now().isoformat()
    })
    
    # If we have all the information, try to generate search queries
    if not state.missing_info and not state.queries_generated:
        try:
            # Create the search queries
            state.search_queries = create_flight_search_queries(state.travel_details)
            state.queries_generated = True
        except Exception as e:
            print(f"Error generating search queries: {str(e)}")
    
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