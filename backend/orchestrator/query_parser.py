#!/usr/bin/env python
"""
Query Parser for Travel Assistant

This module parses natural language travel queries and converts them into
structured search parameters for the Nova Act workers.
"""

import os
from datetime import datetime, date, timedelta
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Import the query generator at the bottom to avoid circular imports

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class TravelQueryDetails(BaseModel):
    """Extracted travel details from user query"""
    origin: Optional[str] = Field(None, description="Origin city or airport code")
    destination: List[str] = Field(default_factory=list, description="Destination city or airport code(s)")
    budget: Optional[float] = Field(None, description="Total budget for the trip")
    trip_length_days: Optional[int] = Field(None, description="Length of the trip in days")
    earliest_start_date: Optional[date] = Field(None, description="Earliest possible start date")
    latest_start_date: Optional[date] = Field(None, description="Latest possible start date")
    specific_month: Optional[str] = Field(None, description="If user specified a month (e.g., 'June')")
    flexible_dates: bool = Field(False, description="Whether dates are flexible")


class FlightSearchQuery(BaseModel):
    """A specific flight search query to run"""
    origin: str = Field(..., description="Origin city or airport code")
    destination: str = Field(..., description="Destination city or airport code")
    depart_date: date = Field(..., description="Departure date")
    return_date: date = Field(..., description="Return date")
    budget: Optional[float] = Field(None, description="Budget constraint")


class QueryParsingResult(BaseModel):
    """Result of query parsing with detailed travel parameters and search queries"""
    details: TravelQueryDetails = Field(..., description="Extracted travel details")
    search_queries: List[FlightSearchQuery] = Field(..., description="Generated search queries to run")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the parsing accuracy")
    missing_info: List[str] = Field(default_factory=list, description="Information missing from the query")


# Create the model and agent exactly as shown in the documentation
model = OpenAIModel('gpt-4o-mini', provider=OpenAIProvider(api_key=OPENAI_API_KEY))

query_parser = Agent(
    model,
    output_type=QueryParsingResult,
    system_prompt="""
    You are a travel query parser. Your task is to extract detailed travel information from 
    user queries and generate specific flight search parameters.
    
    CRITICAL INFORMATION REQUIREMENTS:
    - Origin city or airport (ALWAYS required unless explicitly provided by user)
    - Specific destination (city, not just country or state - e.g., "San Francisco" not just "California")
    - Trip length or duration
    - Date information (REQUIRED - can be specific dates, a month, multiple months, or date range)
    
    IMPORTANT ABOUT DATES:
    - Some form of date information is ALWAYS required - do not make date assumptions
    - This can be specific dates (e.g., "June 10-15"), a month ("June"), multiple months ("June or July"), or a season ("summer")
    - If the user says "flexible" about dates, you must still know the general timeframe (which month or months)
    - If no date information is provided, ALWAYS mark this as missing information
    
    NON-CRITICAL INFORMATION (helpful but not required immediately):
    - Budget
    - Preferences for activities or accommodations
    
    For date ranges:
    - If a specific month is mentioned (e.g., 'June'), generate date options throughout that month
    - If trip length is specified (e.g., '3-day trip'), ensure return dates match that duration
    - For "weekend", assume 2-3 day trip over a weekend (Friday-Sunday)
    
    For locations:
    - Always mark origin as missing unless clearly specified by the user
    - For destinations, always require specific cities/locations, not just regions/countries
    - For example, if user says "California", mark "Specific location within California" as missing
    
    For budget:
    - Extract total budget amounts if specified but don't prioritize asking for it
    - This is non-critical information that can be provided later
    
    If the user says they are flexible on dates or destination, or says 'any' or 'no preference,' treat that as complete information for that field and do not ask for further clarification.
    
    When generating search queries, create a reasonable set of specific date combinations
    that satisfy the constraints. For example, if 'June' is mentioned for a '3-day trip',
    generate all options like Jun 1-4, Jun 8-11, Jun 15-18, etc.
    
    In your final response, the missing_info field MUST include ALL critical information that is missing.
    Double-check your missing_info list before finalizing your response.
    """
)


async def create_flight_search_queries(details: TravelQueryDetails) -> List[FlightSearchQuery]:
    """Create flight search queries from travel details using the LLM-powered query generator"""
    # Import the query generator here to avoid circular imports
    from orchestrator.query_generator import create_travel_search_queries
    
    # Call the LLM-powered query generator
    result = await create_travel_search_queries(details)
    return result["flight_queries"]


async def parse_travel_query(query_text: str) -> QueryParsingResult:
    """
    Parse a natural language travel query into structured search parameters.
    
    Args:
        query_text: Natural language query from the user
        
    Returns:
        QueryParsingResult with travel details and search queries
    """
    # Use Pydantic AI agent to parse the query
    result = await query_parser.run(query_text)
    return result.output


def parse_travel_query_sync(query_text: str) -> QueryParsingResult:
    """Synchronous version of parse_travel_query for use in non-async contexts"""
    import asyncio
    
    # Use an existing event loop if available, otherwise create one
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(parse_travel_query(query_text))


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def test():
        query = "I want a 3-day trip to Seattle in mid-June, budget ≈$800."
        result = await parse_travel_query(query)
        print(f"Travel Details: {result.details}")
        print(f"Generated {len(result.search_queries)} search queries")
        for i, query in enumerate(result.search_queries):
            print(f"Query {i+1}: {query.depart_date} to {query.return_date}")
        print(f"Confidence: {result.confidence}")
        if result.missing_info:
            print(f"Missing information: {', '.join(result.missing_info)}")
    
    asyncio.run(test()) 