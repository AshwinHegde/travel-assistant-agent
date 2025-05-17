#!/usr/bin/env python
"""
Nova Act Worker: Flight Search

Simple flight search using Nova Act.
"""

import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from nova_act import NovaAct

# Import models
sys.path.append(str(Path(__file__).parent.parent))
from orchestrator.models import FlightSearchInput, FlightOption, FlightSearchResults

# Load environment variables from the backend directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def search_flights(search_input: FlightSearchInput) -> FlightSearchResults:
    """Search for flights using Nova Act to interact with Google Flights."""
    api_key = os.environ.get("NOVA_ACT_API_KEY")
    
    # Format dates for prompts
    depart_date_obj = datetime.strptime(search_input.depart_date, "%Y-%m-%d")
    depart_date_formatted = depart_date_obj.strftime("%b %d")  # "Jun 14"
    
    return_date_obj = datetime.strptime(search_input.return_date, "%Y-%m-%d")
    return_date_formatted = return_date_obj.strftime("%b %d")  # "Jun 17"
    
    # Initialize Nova Act and perform search in a single function
    with NovaAct(
        starting_page="https://www.google.com/travel/flights",
        nova_act_api_key=api_key,
        headless=True
    ) as nova:
        # Create search prompt
        search_prompt = f"Search for flights from {search_input.origin} to {search_input.destination} departing on {depart_date_formatted} and returning on {return_date_formatted}"
            
        if search_input.budget:
            search_prompt += f" with a budget of ${search_input.budget}"
            
        if search_input.max_stops is not None:
            search_prompt += f" with maximum {search_input.max_stops} stops"
            
        if search_input.preferred_airlines:
            airlines = ", ".join(search_input.preferred_airlines)
            search_prompt += f" preferring airlines: {airlines}"
        
        # Execute search
        nova.act(search_prompt)
        
        # Define the extraction prompt
        extraction_prompt = "Return the top 5 flight options with airline, flight number, departure time, arrival time, duration, stops, price as JSON"
        
        # Pass the schema from FlightOption to guide the extraction
        result = nova.act(extraction_prompt, schema=List[FlightOption].model_json_schema())
        
        # Parse the results
        flight_options = []
        if result.matches_schema and result.parsed_response:
            # Directly validate the parsed response with our model
            flight_options = [FlightOption.model_validate(flight) for flight in result.parsed_response]
                
        # Return results as a FlightSearchResults object
        return FlightSearchResults(
            options=flight_options,
            search_params=search_input
        )

def main():
    """Parse arguments and run search."""
    parser = argparse.ArgumentParser(description="Flight search with Nova Act")
    parser.add_argument("--origin", required=True, help="Origin airport/city")
    parser.add_argument("--destination", required=True, help="Destination airport/city")
    parser.add_argument("--depart", required=True, help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--return", dest="return_date", required=True, help="Return date (YYYY-MM-DD)")
    parser.add_argument("--budget", type=float, help="Maximum budget")
    parser.add_argument("--travelers", type=int, default=1, help="Number of travelers")
    parser.add_argument("--max-stops", type=int, help="Maximum number of stops")
    parser.add_argument("--airlines", help="Preferred airlines (comma-separated)")
    
    args = parser.parse_args()
    
    # Convert arguments to FlightSearchInput
    search_input = FlightSearchInput(
        origin=args.origin,
        destination=args.destination,
        depart_date=args.depart,
        return_date=args.return_date,
        budget=args.budget,
        num_travelers=args.travelers,
        max_stops=args.max_stops,
        preferred_airlines=args.airlines.split(",") if args.airlines else []
    )
    
    results = search_flights(search_input=search_input)
    
    # Output as JSON
    print(json.dumps(results.model_dump(), default=str))
    return 0

if __name__ == "__main__":
    sys.exit(main())
