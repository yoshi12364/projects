Agent Discovery + Usage Platform

A small FastAPI app that lets you register agents, search for them, and track usage between them.
Built for the intern screening assignment.


How to run

pip install fastapi uvicorn
uvicorn main:app --reload

Then open http://localhost:8000/docs to test the endpoints interactively.


Endpoints

POST /agents
Register a new agent.

{
  "name": "DocParser",
  "description": "Extracts structured data from PDFs",
  "endpoint": "https://api.example.com/parse"
}

GET /agents
Returns all registered agents.

GET /search?q=pdf
Searches by name or description. Case-insensitive.

POST /usage
Log a usage event between two agents.

{
  "caller": "AgentA",
  "target": "DocParser",
  "units": 10,
  "request_id": "abc123"
}

If the same request_id is sent again it won't be counted twice.

GET /usage-summary
Returns total units used per agent sorted highest first.

Example output:
DocParser 120
Summarizer 80


Edge cases handled

Logging usage for an agent that doesn't exist returns a 404 error.
Duplicate request_id means the second request is ignored and not counted.
Missing or invalid fields return a 400 with a clear message.
Empty agent name or bad endpoint URL gives a validation error at registration time.


Design questions

How would you handle billing without double charging?

The request_id deduplication we already have is basically the core of this. For real billing I would persist every usage event to a database with request_id as a unique key so even if a retry comes in the DB insert just fails silently and we don't charge again. On top of that I would run a daily reconciliation job that checks if any usage events didn't make it to the billing table just as a safety net. The billing system would read from that table not from the live usage counter.

How would you store this if scale goes to 100K agents?

In memory dicts obviously won't work at that scale. I would move to PostgreSQL with agents in one table with a unique index on name and usage events in another table with request_id as a unique constraint. For search PostgreSQL ILIKE works fine up to a point but at 100K agents I would probably add something like Typesense or use a tsvector index for full text search. For the usage summary instead of keeping a running counter in memory I would do a GROUP BY query with proper indexing on the target column.


Reflection on AI usage

I used Claude to review my edge case handling after I wrote the first version. Specifically I asked it to check if there were any cases I missed in the usage endpoint. It pointed out I wasn't checking for empty strings in caller and target which I then added.

The core structure the idempotency logic and the tag extraction I figured out on my own. I didn't use AI for the design question answers since those are about trade-offs I've read about while learning backend stuff.
