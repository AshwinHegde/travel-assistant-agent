#!/usr/bin/env python
"""
Travel Search Query Generator

This module generates specific search queries for flights and hotels based on
parsed travel constraints, with awareness of calendar information like weekends and holidays.
"""

import os
import json
import calendar
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

import holidays
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# Do not import query_parser directly to avoid circular dependencies
# We'll import TravelQueryDetails and FlightSearchQuery inside the functions that need them

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Helper function to get the current year with option to override
def get_current_year(override_year: Optional[int] = 2025) -> int:
    """Get the current year, with option to override for testing or specific scenarios"""
    if override_year:
        return override_year
    return datetime.now().year

# Configure the model
model = OpenAIModel('gpt-4o-mini', provider=OpenAIProvider(api_key=OPENAI_API_KEY))


class TravelSearchOptions(BaseModel):
    """Concrete search parameters based on parsed constraints"""
    flight_queries: List[Dict[str, Any]] = Field(default_factory=list,
        description="List of flight search parameters with specific dates")
    hotel_queries: List[Dict[str, Any]] = Field(default_factory=list,
        description="List of hotel search parameters with specific dates")
    explanation: str = Field("", 
        description="Brief explanation of the search strategy")


def get_calendar_information(start_date: date, end_date: date, country_code: str = 'US') -> Dict[str, Any]:
    """
    Get calendar information (weekends and holidays) for a given date range.
    
    Args:
        start_date: The start date of the range
        end_date: The end date of the range
        country_code: The country code for holidays (default: 'US')
        
    Returns:
        Dictionary with weekend dates and holidays in the range
    """
    # Get all dates in the range
    date_range = []
    current_date = start_date
    while current_date <= end_date:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Identify weekends (Saturday=5, Sunday=6 in Python's calendar)
    weekends = [d for d in date_range if d.weekday() >= 5]
    
    # Get holidays for the specified country
    country_holidays = holidays.country_holidays(country_code, years=list(range(start_date.year, end_date.year + 1)))
    holidays_in_range = {d: name for d, name in country_holidays.items() if start_date <= d <= end_date}
    
    return {
        "weekends": [d.isoformat() for d in weekends],
        "holidays": {d.isoformat(): name for d, name in holidays_in_range.items()},
        "is_weekend": {d.isoformat(): (d.weekday() >= 5) for d in date_range},
        "is_holiday": {d.isoformat(): (d in holidays_in_range) for d in date_range},
    }


def get_month_range(month_name: str, year: Optional[int] = None) -> Tuple[date, date]:
    """
    Get the date range for a specified month.
    
    Args:
        month_name: Name of the month (e.g., 'June')
        year: Year (defaults to current year or next year if the month has passed)
        
    Returns:
        Tuple of (first_day, last_day) of the month
    """
    # Convert month name to number
    try:
        month_num = datetime.strptime(month_name, "%B").month
    except ValueError:
        # Try abbreviated month names
        month_num = datetime.strptime(month_name[:3], "%b").month
    
    # Determine year if not specified
    if year is None:
        current_year = get_current_year()
        current_date = date.today().replace(year=current_year)
        year = current_year
        # If the month has already passed this year, use next year
        if month_num < current_date.month:
            year += 1
    
    # Get last day of the month
    _, last_day = calendar.monthrange(year, month_num)
    
    return (date(year, month_num, 1), date(year, month_num, last_day))


# Initialize the agent with customizable system prompt
SYSTEM_PROMPT = """
You generate concrete search queries for flights and hotels based on the user's parsed travel constraints.

Your task is to:
1. Consider the current date: {current_date}
2. Take the destinations and date constraints already identified
3. Generate 5-8 well-distributed specific date combinations 
4. Create both flight and hotel search parameters for each option

When generating dates:
- If month is specified, distribute options throughout that month
- If user mentioned weekends, prioritize weekend options (dates in weekends: {weekends})
- Consider holidays: {holidays}
- Always respect the trip_length_days parameter
- Ensure departure and return dates make sense for the trip length

For weekend trips:
- Favor Friday departure, Sunday/Monday return
- For longer trips, include at least one weekend if possible

For destinations:
- Use exactly the destinations provided in the constraints
- Create one flight query and one hotel query for each date pair and destination

Keep the output focused and practical - real search parameters 
that could be sent to travel search engines.

For flights, include only:
- origin
- destination
- depart_date (ISO format: YYYY-MM-DD)
- return_date (ISO format: YYYY-MM-DD)
- budget (if specified)

For hotels, include only:
- destination/location
- check_in_date (ISO format: YYYY-MM-DD)
- check_out_date (ISO format: YYYY-MM-DD)
- budget (if specified)

Your explanation should briefly describe your strategy (e.g., "Prioritized weekend options in June" or 
"Distributed searches across weekends in the summer").
"""

search_generator = Agent(
    model,
    output_type=TravelSearchOptions,
    system_prompt=SYSTEM_PROMPT
)


async def generate_search_queries(details) -> TravelSearchOptions:
    """
    Generate concrete search queries based on parsed travel details.
    Takes parsed constraints and produces specific date-based queries with
    awareness of calendar information like weekends and holidays.
    """
    # Import TravelQueryDetails for type hints only
    from orchestrator.query_parser import TravelQueryDetails
    
    # Get current date with appropriate year
    current_year = get_current_year()
    today = date.today().replace(year=current_year)
    
    # Determine date range based on constraints
    if details.specific_month:
        start_date, end_date = get_month_range(details.specific_month)
    elif details.earliest_start_date:
        start_date = details.earliest_start_date
        end_date = details.latest_start_date or (start_date + timedelta(days=30))
    else:
        # Default: next 2 months
        start_date = today + timedelta(days=14)  # Start 2 weeks from now
        end_date = today + timedelta(days=75)    # Look ahead about 2.5 months
    
    # Get calendar information (weekends and holidays)
    calendar_info = get_calendar_information(start_date, end_date)
    
    # Format the constraints for the LLM
    constraints = {
        "origin": details.origin or "Unknown",
        "destinations": details.destination,
        "trip_length_days": details.trip_length_days or 7,  # Default to 1 week if not specified
        "specific_month": details.specific_month,
        "date_range_start": details.earliest_start_date.isoformat() if details.earliest_start_date else start_date.isoformat(),
        "date_range_end": details.latest_start_date.isoformat() if details.latest_start_date else end_date.isoformat(),
        "flexible_dates": details.flexible_dates,
        "budget": details.budget,
        "current_date": today.isoformat(),
        "weekends": calendar_info["weekends"],
        "holidays": calendar_info["holidays"]
    }
    
    # Format the system prompt with calendar information
    formatted_prompt = SYSTEM_PROMPT.format(
        current_date=today.isoformat(),
        weekends=", ".join(calendar_info["weekends"][:10]),  # First 10 weekends
        holidays=", ".join(f"{d} ({name})" for d, name in list(calendar_info["holidays"].items())[:8])  # First 8 holidays
    )
    
    # Use an updated system prompt with the calendar info
    result = await search_generator.run(
        json.dumps(constraints),
        system_prompt=formatted_prompt
    )
    
    return result.output


async def create_travel_search_queries(details) -> Dict[str, Any]:
    """
    Create search queries for both flights and hotels based on parsed details.
    """
    # Import needed classes for conversion
    from orchestrator.query_parser import FlightSearchQuery
    
    # Get LLM-generated search queries
    search_options = await generate_search_queries(details)
    
    # Convert flight queries to FlightSearchQuery objects
    flight_queries = []
    for query in search_options.flight_queries:
        # Ensure dates are date objects
        depart_date = query["depart_date"]
        return_date = query["return_date"]
        if isinstance(depart_date, str):
            depart_date = date.fromisoformat(depart_date)
        if isinstance(return_date, str):
            return_date = date.fromisoformat(return_date)
        
        flight_query = FlightSearchQuery(
            origin=query["origin"],
            destination=query["destination"],
            depart_date=depart_date,
            return_date=return_date,
            budget=query.get("budget", details.budget)
        )
        flight_queries.append(flight_query)
    
    # Return both raw queries and structured objects
    return {
        "flight_queries": flight_queries,
        "hotel_queries": search_options.hotel_queries,
        "raw_flight_queries": search_options.flight_queries,
        "explanation": search_options.explanation
    }
