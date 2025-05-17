Here are three core user-flows we want to build with the orchestrator + Nova Act scraping:

1. Initial Trip Kick-off
User: “I want a 3-day trip to Seattle in mid-June, budget ≈$800.”

Orchestrator

Parses intent → { domain: flights, dates: Jun 14–17, budget:800 } & { domain: hotels, dates: same, budget_per_night: ~200 }

Fires off two Nova Act workers in parallel (flights + hotels)

Nova Act Workers

Scrape flight aggregators for best outbound/inbound

Scrape hotel listings filtered by price/rating

Orchestrator

Normalizes, ranks top 3 flight+hotel combos

Returns a summary card: ✈️ Flight details + 🏨 Hotel name & price

Goal: Show “Package” results in one go.

2. Budget or Preference Refinement
User: “Those hotels are too pricey—show me cheaper or change neighborhood to Capitol Hill.”

Orchestrator

Updates the session state (lower max hotel price OR new area filter)

Triggers only the hotel Nova Act worker

Nova Act Hotel Worker

Re-scrapes with updated filters

Orchestrator

Sends back refreshed hotel-only cards, plus how they affect the combined package cost

Goal: Minimal re-scraping, fast turnaround on tweaks.

3. Date-Shift & Add-On Experiences
User: “Actually, shift trip one week later and add a half-day whale-watching tour.”

Orchestrator

Adjusts date window to Jun 21–24

Fires flights + hotels workers (since dates changed) and a 3rd worker for “experiences”

Nova Act Workers

Flights + hotels scrape for new dates

Experiences scrape (e.g. Viator) for “whale watching” availability

Orchestrator

Bundles new flight+hotel combos and whale-watch slots

Presents as a single refreshed itinerary with prices/time slots

Goal: Seamless “date adjustment + feature add” in one conversational turn.

Focusing on these flows will let you demo:

Parallel scraping (Nova Act)

Smart orchestration (only rerun what changed)

Iterative, natural language refinement in a single day.