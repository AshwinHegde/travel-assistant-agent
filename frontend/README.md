# Travel Assistant Agent Frontend

This is the frontend for the Travel Assistant Agent, built with Next.js and shadcn/ui components.

## Features

- Interactive chat interface
- Session management for multi-turn conversations
- Travel search results display

## Setup and Installation

### Prerequisites

- Node.js 18+ and npm
- Backend service running (see backend setup)

### Installation

1. Install dependencies:

```bash
npm install
```

2. Run the development server:

```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Running the Complete System

1. Start the backend server:

```bash
# From the backend directory
poetry run uvicorn app:app --reload
```

2. Start the frontend development server:

```bash
# From the frontend directory
npm run dev
```

3. The frontend will proxy API requests to the backend to avoid CORS issues.

## How to Use

1. Enter your travel request in the chat interface
2. The assistant will ask follow-up questions for any missing details
3. Once all necessary information is collected, travel options will be displayed
4. You can continue the conversation to refine your search

## Example Queries

- "I want to go on vacation"
- "I'm looking for a trip to Seattle in June"
- "I need a 3-day weekend trip to New York with a budget of $800"
