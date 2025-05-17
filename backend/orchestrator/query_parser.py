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

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class TravelQueryDetails(BaseModel):
    """Extracted travel details from user query"""
    origin: Optional[str] = Field(None, description="Origin city or airport code")
    destination: str = Field(..., description="Destination city or airport code")
    budget: Optional[float] = Field(None, description="Total budget for the trip")
    trip_length_days: Optional[int] = Field(None, description="Length of the trip in days")
    earliest_start_date: Optional[date] = Field(None, description="Earliest possible start date")
    latest_start_date: Optional[date] = Field(None, description="Latest possible start date")
    specific_month: Optional[str] = Field(None, description="If user specified a month (e.g., 'June')")
    travelers: int = Field(1, description="Number of travelers")
    flexible_dates: bool = Field(False, description="Whether dates are flexible")
    preferred_airlines: List[str] = Field(default_factory=list, description="Preferred airlines if specified")
    max_stops: Optional[int] = Field(None, description="Maximum number of stops")


class FlightSearchQuery(BaseModel):
    """A specific flight search query to run"""
    origin: str = Field(..., description="Origin city or airport code")
    destination: str = Field(..., description="Destination city or airport code")
    depart_date: date = Field(..., description="Departure date")
    return_date: date = Field(..., description="Return date")
    budget: Optional[float] = Field(None, description="Budget constraint")
    travelers: int = Field(1, description="Number of travelers")
    max_stops: Optional[int] = Field(None, description="Maximum number of stops")
    preferred_airlines: List[str] = Field(default_factory=list, description="Preferred airlines")


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
    
    For date ranges:
    - If a specific month is mentioned (e.g., "June"), generate date options throughout that month
    - If trip length is specified (e.g., "3-day trip"), ensure return dates match that duration
    - Default to searching dates 2-3 months from the current date if no specific dates
    
    For locations:
    - Default origin is the user's current location if not specified
    - Extract destination cities, regions, or countries
    
    For budget:
    - Extract total budget amounts if specified
    - Default to medium price range if not specified
    
    When generating search queries, create a reasonable set of specific date combinations
    that satisfy the constraints. For example, if "June" is mentioned for a "3-day trip",
    generate all options like Jun 1-4, Jun 8-11, Jun 15-18, etc.
    
    Include all relevant details and highlight any missing information that would be needed
    for a complete search.
    """
)


def generate_date_options(details: TravelQueryDetails) -> List[tuple[date, date]]:
    """Generate date options based on the extracted travel details"""
    today = date.today()
    date_pairs = []
    
    # If specific month mentioned, generate options throughout that month
    if details.specific_month:
        try:
            # Convert month name to month number
            month_num = datetime.strptime(details.specific_month, "%B").month
            
            # If month is in the past for this year, assume next year
            year = today.year
            if month_num < today.month:
                year += 1
                
            # Define start and end constraints
            month_start = date(year, month_num, 1)
            
            # Get days in month
            if month_num == 12:
                next_month = date(year + 1, 1, 1)
            else:
                next_month = date(year, month_num + 1, 1)
            month_end = next_month - timedelta(days=1)
            
            # Generate date pairs based on trip length
            trip_length = details.trip_length_days or 3  # Default to 3 days if not specified
            
            # Generate a reasonable number of options (not too many)
            step = 5 if trip_length <= 3 else 3  # Shorter trips can have more options
            
            current_start = month_start
            while current_start <= month_end - timedelta(days=trip_length):
                current_end = current_start + timedelta(days=trip_length)
                if current_end <= month_end:
                    date_pairs.append((current_start, current_end))
                current_start += timedelta(days=step)
        except ValueError:
            # Fallback if month parsing fails
            pass
    
    # If explicit date range specified
    elif details.earliest_start_date and details.trip_length_days:
        latest_start = details.latest_start_date or (details.earliest_start_date + timedelta(days=14))
        trip_length = details.trip_length_days
        
        current_start = details.earliest_start_date
        while current_start <= latest_start:
            date_pairs.append((current_start, current_start + timedelta(days=trip_length)))
            current_start += timedelta(days=3)  # Skip forward by 3 days each time
    
    # Fallback to near future dates
    else:
        trip_length = details.trip_length_days or 3
        future_start = today + timedelta(days=30)  # Start 1 month from now
        
        for i in range(0, 30, 7):  # Generate options over several weeks
            start_date = future_start + timedelta(days=i)
            end_date = start_date + timedelta(days=trip_length)
            date_pairs.append((start_date, end_date))
    
    return date_pairs


def create_flight_search_queries(details: TravelQueryDetails) -> List[FlightSearchQuery]:
    """Create flight search queries from travel details"""
    date_pairs = generate_date_options(details)
    
    # Default to "SEA" as origin if not specified (just as an example)
    origin = details.origin or "SEA"
    
    search_queries = []
    for depart_date, return_date in date_pairs:
        query = FlightSearchQuery(
            origin=origin,
            destination=details.destination,
            depart_date=depart_date,
            return_date=return_date,
            budget=details.budget,
            travelers=details.travelers,
            max_stops=details.max_stops,
            preferred_airlines=details.preferred_airlines,
        )
        search_queries.append(query)
    
    return search_queries


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
    # Use Pydantic AI agent to parse the query
    result = query_parser.run_sync(query_text)
    return result.output


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