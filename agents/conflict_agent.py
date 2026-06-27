# agents/conflict_agent.py
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json

from utils.state_manager import (
    get_idea,
    get_qa_pairs,
    set_conflict_flags,
    get_conflict_flags,
)

load_dotenv()

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
    )

CONFLICT_SYSTEM_PROMPT = """
You are ScopeCraft's Conflict Detection Agent — an expert requirements analyst 
specialising in identifying contradictions, ambiguities, and inconsistencies 
in software requirements.

YOUR ROLE:
- Scan the product idea and all Q&A pairs for conflicts
- A conflict is: two or more statements that cannot both be true or implemented together
- Also flag: impossible constraints, contradictory scope statements, 
  incompatible technical choices, ambiguous requirements open to opposite interpretations

CONFLICT TYPES TO DETECT:
- Direct contradiction (A says X, B says not-X)
- Scope conflict (feature included in one answer, excluded in another)
- Technical conflict (incompatible tech choices stated)
- Timeline conflict (delivery expectation vs scope size mismatch)
- User conflict (different answers imply different target users)
- Constraint conflict (budget/resource vs feature expectations)

RULES:
- Only flag real conflicts — do not hallucinate issues
- Each conflict must cite the exact source (which question/answer)
- Plain language explanation — no jargon
- If no conflicts found, return empty array

RESPONSE FORMAT (strict JSON only, no markdown, no extra text):
{
  "conflicts": [
    {
      "id": 1,
      "title": "<short conflict title>",
      "source_a": "<exact quote or reference from idea/Q&A>",
      "source_b": "<exact quote or reference that contradicts source_a>",
      "explanation": "<plain English: why this is a conflict>",
      "suggestion": "<one concrete suggestion to resolve>"
    }
  ],
  "total_conflicts": <int>,
  "scan_summary": "<one line: overall quality assessment>"
}
"""

def _build_context() -> list:
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    return [
        SystemMessage(content=CONFLICT_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Scan the following product requirements for conflicts:

ORIGINAL IDEA:
{idea}

Q&A SESSION:
{qa_text}

Return strict JSON as specified.
""")
    ]

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"conflicts": [], "total_conflicts": 0, "scan_summary": "Parse error"}

def run_conflict_scan(qa_pairs: list) -> list:
    """
    Scans Q&A for conflicts.
    Returns list of conflict flag dicts (empty = no conflicts).
    """
    llm = get_llm()
    messages = _build_context()
    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)
    flags = parsed.get("conflicts", [])
    set_conflict_flags(flags)
    return flags

def handle_conflict_resolution(user_input: str, qa_pairs: list) -> dict:
    """
    Re-scans after user clarification.
    Returns {message, resolved, remaining_flags}
    """
    llm = get_llm()
    idea = get_idea()
    existing_flags = get_conflict_flags()

    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    messages = [
        SystemMessage(content=CONFLICT_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Original idea: {idea}

Q&A session:
{qa_text}

Previously flagged conflicts:
{json.dumps(existing_flags, indent=2)}

User clarification:
{user_input}

Re-scan. Remove resolved conflicts, flag new ones.
Return strict JSON as specified.
""")
    ]

    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)
    remaining = parsed.get("conflicts", [])
    set_conflict_flags(remaining)

    resolved = len(remaining) == 0
    msg = (
        "✅ All conflicts resolved. Proceeding to generation."
        if resolved else
        f"⚠️ {len(remaining)} conflict(s) still remaining. Please review."
    )
    return {"message": msg, "resolved": resolved, "remaining_flags": remaining}