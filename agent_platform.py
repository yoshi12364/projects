from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import re

app = FastAPI()

# just using dicts for now, good enough for this scope
agent_registry = {}
usage_records = {}  # keyed by request_id to handle duplicates
usage_totals = {}   # target agent -> total units used


# --- models ---

class Agent(BaseModel):
    name: str
    description: str
    endpoint: str

class UsageEntry(BaseModel):
    caller: str
    target: str
    units: int
    request_id: str


# tag extraction (no LLM, just basic keyword logic) 

def get_tags(text: str):
    skip = {"a", "an", "the", "and", "or", "is", "in", "of",
            "to", "for", "from", "that", "it", "by", "with", "on", "are", "this"}
    words = re.findall(r"[a-zA-Z]+", text.lower())
    tags = []
    seen = set()
    for w in words:
        if w not in skip and w not in seen and len(w) > 2:
            tags.append(w)
            seen.add(w)
    return tags


# agent endpoints

@app.post("/agents", status_code=201)
def register_agent(agent: Agent):
    if not agent.name.strip():
        raise HTTPException(status_code=400, detail="Agent name can't be empty")
    if not agent.endpoint.startswith("http"):
        raise HTTPException(status_code=400, detail="Endpoint should be a valid URL")

    tags = get_tags(agent.description)

    agent_registry[agent.name] = {
        "name": agent.name,
        "description": agent.description,
        "endpoint": agent.endpoint,
        "tags": tags
    }

    return {"status": "registered", "agent": agent_registry[agent.name]}


@app.get("/agents")
def list_agents():
    return list(agent_registry.values())


@app.get("/search")
def search_agents(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Search query can't be empty")

    q_lower = q.lower()
    results = []

    for agent in agent_registry.values():
        if (q_lower in agent["name"].lower() or
            q_lower in agent["description"].lower()):
            results.append(agent)

    return results


# usage endpoints

@app.post("/usage")
def log_usage(entry: UsageEntry):
    if not entry.caller.strip() or not entry.target.strip():
        raise HTTPException(status_code=400, detail="caller and target are required")

    if entry.units <= 0:
        raise HTTPException(status_code=400, detail="units must be greater than 0")

    # check target agent actually exists
    if entry.target not in agent_registry:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{entry.target}' not found. Please register it first."
        )

    if entry.request_id in usage_records:
        return {"status": "duplicate", "message": "This request_id was already logged, skipping"}

    usage_records[entry.request_id] = entry.dict()

    if entry.target not in usage_totals:
        usage_totals[entry.target] = 0
    usage_totals[entry.target] += entry.units

    return {"status": "logged", "entry": entry.dict()}


@app.get("/usage-summary")
def get_usage_summary():
    if not usage_totals:
        return {"message": "No usage data yet"}

    summary = [
        {"agent": agent, "total_units": total}
        for agent, total in sorted(usage_totals.items(), key=lambda x: x[1], reverse=True)
    ]

    return summary
