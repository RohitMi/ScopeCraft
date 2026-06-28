# agents/hld_agent.py
# HLD Agent — generates High Level Design with Mermaid diagrams

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json

from utils.state_manager import get_idea, get_brd, get_user_stories
from utils.error_handler import llm_call_with_retry

load_dotenv()

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
    )

HLD_SYSTEM_PROMPT = """
You are ScopeCraft's HLD Agent — a senior Solution Architect that produces
High Level Design documents with Mermaid diagrams.

Generate a HLD document with EXACTLY these sections:

# High Level Design

## 1. Architecture Overview
<2-3 paragraphs: architectural style chosen, key decisions, rationale>

## 2. System Context Diagram
<Mermaid C4 context diagram showing system + external actors>

```mermaid
graph TD
    User[👤 User] --> System[🔭 System Name]
    System --> ExtService[External Service]
```

## 3. Component Architecture
<Mermaid diagram showing internal components and their relationships>

```mermaid
graph LR
    subgraph Frontend
        UI[UI Layer]
    end
    subgraph Backend
        API[API Layer]
        BL[Business Logic]
    end
    subgraph Data
        DB[(Database)]
    end
    UI --> API
    API --> BL
    BL --> DB
```

## 4. Data Flow Diagram
<Mermaid sequence diagram showing key user journey end-to-end>

```mermaid
sequenceDiagram
    actor User
    participant Frontend
    participant Backend
    participant Database
    User->>Frontend: Action
    Frontend->>Backend: API Call
    Backend->>Database: Query
    Database-->>Backend: Result
    Backend-->>Frontend: Response
    Frontend-->>User: Display
```

## 5. Technology Stack Recommendation
| Layer | Technology | Reason |
|-------|------------|--------|

## 6. Key Design Decisions
| Decision | Choice | Rationale | Trade-off |
|----------|--------|-----------|-----------|

## 7. Scalability & Risk Notes
<Bullet list of scaling considerations and technical risks>

RULES:
- All diagrams must be valid Mermaid syntax
- Use actual product components from BRD — no generic placeholders
- Technology recommendations must match the product type and scale
- Keep diagrams clean — max 10 nodes per diagram
- Return STRICT JSON only

RESPONSE FORMAT:
{
  "hld": "<full HLD markdown with embedded Mermaid diagrams>",
  "hld_summary": "<one line: architecture style + key tech choices>"
}
"""

def _build_context(brd: str, user_stories: str, idea: str) -> list:
    return [
        SystemMessage(content=HLD_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate HLD from these requirements:

ORIGINAL IDEA:
{idea}

BRD (primary reference):
{brd}

USER STORIES (for component scope):
{user_stories}

Produce full HLD with valid Mermaid diagrams.
Return strict JSON only.
""")
    ]

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "hld": raw,
            "hld_summary": "Parse error on HLD generation"
        }

def run_hld_generation() -> str:
    """
    Generates HLD + Mermaid diagrams from BRD + User Stories.
    Returns hld markdown string.
    """
    llm = get_llm()
    idea = get_idea()
    brd = get_brd()
    user_stories = get_user_stories()

    if not brd:
        return "⚠️ No BRD found — generate documents first."

    messages = _build_context(brd, user_stories, idea)
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)
    return parsed.get("hld", "")