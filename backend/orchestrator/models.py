#!/usr/bin/env python
"""
Pydantic models for the Travel Assistant Agent

This file contains all the Pydantic models used for:
1. API request/response validation
2. Worker input/output validation 
3. Database models (via SQLModel)
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum


class TravelDomain(str, Enum):
    """Travel domain types that we can search across"""
    FLIGHTS = "flights"
    HOTELS = "hotels"
    EXPERIENCES = "experiences"
    PACKAGES = "packages"


class DateRange(BaseModel):
    """Date range for travel"""
    start_date: date
    end_date: date
    
    @validator("end_date")
    @classmethod
    def end_date_after_start_date(cls, v, values):
        if "start_date" in values and v < values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class Location(BaseModel):
    """Location information"""
    city: str
    country: Optional[str] = None
    region: Optional[str] = None
    airport_code: Optional[str] = None


class TravelPreference(BaseModel):
    """User preferences for travel"""
    class Config:
        use_enum_values = True
    
    domain: TravelDomain
    importance: int = Field(1, ge=1, le=5, description="Importance from 1-5")


class TravelIntent(BaseModel):
    """Extracted travel intent from user message"""
    origin: Optional[Location] = None
    destination: Location
    date_range: DateRange
    budget: Optional[float] = None
    num_travelers: int = Field(1, ge=1, description="Number of travelers")
    preferences: List[TravelPreference] = []
    flexible_dates: bool = False
    max_stops: Optional[int] = None
    preferred_airlines: List[str] = []
    hotel_stars: Optional[int] = None
    neighborhoods: List[str] = []
    experience_types: List[str] = []


class UserMessage(BaseModel):
    """User message for chat API"""
    user_id: str
    message: str
    session_id: Optional[str] = None


# Worker Input/Output models

class FlightSearchInput(BaseModel):
    """Input for flight search worker"""
    origin: str
    destination: str
    depart_date: str
    return_date: str
    budget: Optional[float] = None
    num_travelers: int = 1
    max_stops: Optional[int] = None
    preferred_airlines: List[str] = []


class FlightOption(BaseModel):
    """Flight search result"""
    airline: str
    flight_number: Optional[str] = None
    departure_time: str  
    arrival_time: str
    duration: str
    stops: int
    price: float
    currency: str = "USD"
    layovers: List[str] = []
    deep_link: Optional[str] = None


class FlightSearchResults(BaseModel):
    """Results from flight search"""
    options: List[FlightOption]
    search_params: FlightSearchInput


class HotelSearchInput(BaseModel):
    """Input for hotel search worker"""
    destination: str
    check_in: str
    check_out: str
    budget_per_night: Optional[float] = None
    num_guests: int = 1
    min_stars: Optional[int] = None
    neighborhoods: List[str] = []
    amenities: List[str] = []


class HotelOption(BaseModel):
    """Hotel search result"""
    name: str
    address: str
    stars: float
    price_per_night: float
    total_price: float
    currency: str = "USD"
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    amenities: List[str] = []
    image_url: Optional[str] = None
    deep_link: Optional[str] = None


class HotelSearchResults(BaseModel):
    """Results from hotel search"""
    options: List[HotelOption]
    search_params: HotelSearchInput


class ExperienceSearchInput(BaseModel):
    """Input for experience search worker"""
    destination: str
    date_range: DateRange
    budget: Optional[float] = None
    num_people: int = 1
    categories: List[str] = []
    keywords: List[str] = []


class ExperienceOption(BaseModel):
    """Experience search result"""
    name: str
    description: str
    price: float
    currency: str = "USD"
    duration: str
    rating: Optional[float] = None
    num_reviews: Optional[int] = None
    image_url: Optional[str] = None
    available_dates: List[date] = []
    available_times: List[str] = []
    deep_link: Optional[str] = None


class ExperienceSearchResults(BaseModel):
    """Results from experience search"""
    options: List[ExperienceOption]
    search_params: ExperienceSearchInput


# Package models (combined results)

class TravelPackage(BaseModel):
    """A complete travel package"""
    package_id: str = Field(..., description="Unique ID for this package")
    flight: Optional[FlightOption] = None
    hotel: Optional[HotelOption] = None
    experiences: List[ExperienceOption] = []
    total_price: float
    currency: str = "USD"


# API Response models

class ChatResponse(BaseModel):
    """Response for the chat API"""
    message: str
    packages: Optional[List[TravelPackage]] = None
    flights: Optional[List[FlightOption]] = None
    hotels: Optional[List[HotelOption]] = None
    experiences: Optional[List[ExperienceOption]] = None
    next_prompts: List[str] = []
    session_id: str 