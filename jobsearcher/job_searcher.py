import asyncio
import time
import requests
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from tavily import TavilyClient


# 1. CLIENT
model_client = OpenAIChatCompletionClient(
    model="mistral-large-latest",
    api_key="G5z8pqiJOcoog6Mwh4vZk4GZn5ZH3tK0",
    base_url="https://api.mistral.ai/v1",
    model_info={
        "vision": False,
        "function_calling": True,
        "json_output": True,
        "family": "mistral",
        "structured_output": False,
    }
)

tavily = TavilyClient(api_key="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")

# 2. RATE LIMIT GUARD
LLM_DELAY = 20

def llm_sleep(label: str = ""):
    print(f"  [⏳ Rate Guard] Sleeping {LLM_DELAY}s before: {label}")
    time.sleep(LLM_DELAY)

# 3. QUERY MAPS

JSEARCH_QUERIES = [
    {
        "role_label": "Generative AI Engineer",
        "primary":    "Generative AI Engineer entry level India",
        "fallback":   "AI Engineer LLM Python India",
    },
    {
        "role_label": "Agentic AI Developer",
        "primary":    "AI Agent Developer LangGraph Python India",
        "fallback":   "AI Developer LangChain entry level India",
    },
    {
        "role_label": "LLM Application Engineer",
        "primary":    "LLM Engineer entry level Hyderabad",
        "fallback":   "NLP Engineer Python entry level India",
    },
    {
        "role_label": "RAG Pipeline Engineer",
        "primary":    "RAG Engineer LangChain Hyderabad",
        "fallback":   "Machine Learning Engineer Python RAG India",
    },
    {
        "role_label": "AI Automation Engineer",
        "primary":    "AI Automation Engineer Python entry level India",
        "fallback":   "Automation Engineer AI ML India junior",
    },
]

TAVILY_QUERIES = [
    ("Generative AI Engineer",   "Generative AI Engineer fresher job Hyderabad 2026 apply"),
    ("Agentic AI Developer",     "Agentic AI Developer entry level job Hyderabad 2026"),
    ("LLM Application Engineer", "LLM Engineer fresher job Hyderabad OR Remote India 2026"),
    ("RAG Pipeline Engineer",    "RAG Engineer LangChain job Hyderabad fresher 2026"),
    ("AI Automation Engineer",   "AI Automation Engineer fresher Hyderabad job 2026"),
]

# ─────────────────────────────────────────────────────────────
# 4. DATA COLLECTION  (no LLM cost)
# ─────────────────────────────────────────────────────────────

def collect_web_results() -> str:
    lines = ["WEB SEARCH DATA (Tavily) "]
    for role_label, query in TAVILY_QUERIES:
        print(f"  [Tavily] {role_label}")
        try:
            resp = tavily.search(query=query, search_depth="basic", max_results=1)
            r = resp.get("results", [{}])[0]
            url     = r.get("url", "N/A")
            snippet = r.get("content", "N/A")[:200]
            lines.append(f"ROLE: {role_label}\nURL: {url}\nSNIPPET: {snippet}\n")
        except Exception as e:
            lines.append(f"ROLE: {role_label} | ERROR: {e}\n")
        time.sleep(2)
    return "\n".join(lines)


def jsearch_query(query: str, max_results: int = 2) -> list:
    headers = {
        "X-RapidAPI-Key":  "7a388faff8msh2d74ced4d069c81p1f59f1jsndb742b15389f",
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    params = {"query": query, "page": "1", "num_pages": "1"}
    try:
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers=headers, params=params, timeout=10,
        )
        return resp.json().get("data", [])[:max_results]
    except Exception as e:
        print(f"    JSearch error: {e}")
        return []


def collect_portal_results() -> str:
    lines = ["JOB PORTAL DATA (JSearch → Indeed/LinkedIn)"]
    total_found = 0

    for item in JSEARCH_QUERIES:
        role_label = item["role_label"]
        print(f"  [JSearch] {role_label}")
        jobs = jsearch_query(item["primary"], max_results=2)

        if not jobs:
            print(f"    ↳ Primary empty. Trying fallback: {item['fallback']}")
            time.sleep(1)
            jobs = jsearch_query(item["fallback"], max_results=2)

        if not jobs:
            lines.append(f"ROLE: {role_label} | No listings found (tried both queries).\n")
        else:
            for j in jobs:
                total_found += 1
                lines.append(
                    f"ROLE: {role_label}\n"
                    f"COMPANY: {j.get('employer_name', 'N/A')}\n"
                    f"TITLE: {j.get('job_title', 'N/A')}\n"
                    f"LOCATION: {j.get('job_city', 'N/A')}, {j.get('job_country', 'N/A')}\n"
                    f"LINK: {j.get('job_apply_link', 'N/A')}\n"
                    f"DESC: {j.get('job_description', '')[:150]}...\n"
                )
        time.sleep(1)

    print(f"  [JSearch] Total listings found: {total_found}")
    return "\n".join(lines)


# 5. GATE TOOLS  (one per agent hand-off)

def gate_to_validator() -> str:
    llm_sleep("data_validator_agent LLM call")
    return "Gate passed. Validate data now."


def gate_to_analyst() -> str:
    llm_sleep("analyst_agent LLM call")
    return "Gate passed. Analyse and score now."


def gate_to_finalizer() -> str:
    llm_sleep("finalizer_agent LLM call")
    return "Gate passed. Format final report now."

# 6. AGENTS


#  Agent 1: Coordinator 
coordinator_agent = AssistantAgent(
    name="coordinator_agent",
    model_client=model_client,
    tools=[gate_to_validator],
    handoffs=["data_validator_agent"],
    system_message="""
You are the Coordinator. Your ONLY job:
1. Call the tool 'gate_to_validator' exactly once.
2. Immediately hand off to 'data_validator_agent'.
Do NOT write any summary, analysis, or commentary.
""",
)

# ── Agent 2: Data Validator ───────────────────────────────────
data_validator_agent = AssistantAgent(
    name="data_validator_agent",
    model_client=model_client,
    tools=[gate_to_analyst],
    handoffs=["analyst_agent"],
    system_message="""
You are the Data Validator. Given raw Tavily + JSearch data:

VALIDATION RULES:
1. Web Search rows (Tavily):
   - Mark URL as INVALID if it is "N/A", empty, or not a real domain.
   - Keep all 5 roles; if a role has no valid URL write URL: INVALID.

2. Job Portal rows (JSearch):
   - Remove any listing where LINK is "N/A" or empty.
   - Flag any listing where LOCATION does not contain India, IN, Hyderabad,
     Telangana, Remote, or Bengaluru — mark it LOCATION_MISMATCH.
   - Keep all 5 roles; if a role ends up with zero listings after removal,
     add a row: "ROLE: <name> | No valid listings after validation."

3. Do NOT invent data. Do NOT change any field values.

OUTPUT FORMAT:
Reproduce the cleaned data using the EXACT same field labels
(ROLE, COMPANY, TITLE, LOCATION, LINK, DESC, URL, SNIPPET).
Prefix each section heading as before.

After outputting cleaned data:
- Call tool 'gate_to_analyst' once.
- Hand off to 'analyst_agent'.
""",
)

# ── Agent 3: Analyst ─────────────────────────────────────────
analyst_agent = AssistantAgent(
    name="analyst_agent",
    model_client=model_client,
    tools=[gate_to_finalizer],
    handoffs=["finalizer_agent"],
    system_message="""
You are the Job Analyst. Candidate profile:
  Skills : Python, LangChain, LangGraph, RAG, LLM, AutoGen, Vector DBs
  Level  : Fresher / 2026 Graduate
  Location: Hyderabad preferred; Remote India acceptable

SCORING RULES — score each Job Portal listing 1–10:
  +3  if description mentions Python, LangChain, LangGraph, RAG, or LLM
  +2  if location is Hyderabad or Remote
  +2  if title contains AI, ML, LLM, NLP, or Generative
  +1  if company is a known tech firm or AI startup
  -2  if LOCATION_MISMATCH flag is present
  Min score = 1, Max score = 10

For Web Search rows: add SCORE: N/A (we can't score snippets reliably).

OUTPUT FORMAT:
Reproduce ALL fields for every listing AND append a SCORE field.
Sort Job Portal listings by SCORE descending within each role group.
Keep section headings identical.

After outputting scored data:
- Call tool 'gate_to_finalizer' once.
- Hand off to 'finalizer_agent'.
""",
)

# ── Agent 4: Finalizer ───────────────────────────────────────
finalizer_agent = AssistantAgent(
    name="finalizer_agent",
    model_client=model_client,
    system_message="""
You are the Report Formatter. Use ONLY the data provided — no hallucination.

STRICT RULES:
- If a field is missing, write N/A.
- If a role has no listings, still include a row with N/A values.
- Descriptions must be ≤ 15 words.
- INVALID URLs → display as "—" in the table.
- LOCATION_MISMATCH listings → add ⚠️ after location.
- Sort Job Portal table by Score column (highest first).

Output EXACTLY THREE Markdown sections:

---

## 🌐 Web Search Results (5 roles)
| # | Role | Source Site | Apply Link |
|---|------|-------------|------------|

---

## 💼 Job Portal Results (up to 10 listings)
| # | Role | Company | Job Title | Location | Score | Apply Link | Description |
|---|------|---------|-----------|----------|-------|------------|-------------|

---

## 📊 Summary
- Total web results : X
- Total portal listings : X (after validation)
- Top scored role : <role> — <company> (Score: X)
- Recommended action : 1-sentence advice for the candidate.

End your response with exactly: TERMINATE
""",
)

# ─────────────────────────────────────────────────────────────
# 7. SWARM  (4 agents)
# ─────────────────────────────────────────────────────────────
aura_swarm = Swarm(
    participants=[
        coordinator_agent,
        data_validator_agent,
        analyst_agent,
        finalizer_agent,
    ],
    termination_condition=TextMentionTermination("TERMINATE"),
)

# ─────────────────────────────────────────────────────────────
# 8. PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────
async def run_pipeline():
    print("=" * 60)
    print("  AURA-SCOUT v4  |  4-Agent Pipeline")
    print("  coordinator → validator → analyst → finalizer")
    print("=" * 60)

    #  Step 1: Tavily web search 
    print("\n[Step 1] Web Search (Tavily)...")
    web_data = collect_web_results()

    # Step 2: JSearch job portal
    print("\n[Step 2] Job Portal (JSearch)...")
    portal_data = collect_portal_results()

    # Debug preview 
    print("\n--- RAW PORTAL DATA PREVIEW (first 800 chars) ---")
    print(portal_data[:800])
    print("-------------------------------------------------\n")

    # Rate guard before first LLM call 
    llm_sleep("coordinator_agent first LLM call")

    task = f"""
CANDIDATE PROFILE
  Name    : 2026 Graduate
  Location: Hyderabad / Remote India
  Skills  : Python, LangChain, LangGraph, RAG, LLM, AutoGen, Vector DBs

{web_data}

{portal_data}

Validate, score, and format the above data into a final report.
Use ONLY the data above. No hallucination.
"""

    # Step 3: Run the 4-agent swarm 
    print("[Step 3] Running 4-Agent Swarm...\n")
    print("  Flow: coordinator → data_validator → analyst → finalizer\n")

    result = await aura_swarm.run(task=task)

    #Final output 
    print("\n" + "=" * 60)
    print("  FINAL JOB REPORT  (AURA-SCOUT v4)")
    print("=" * 60 + "\n")
    print(result.messages[-1].content)

if __name__ == "__main__":
    asyncio.run(run_pipeline())
