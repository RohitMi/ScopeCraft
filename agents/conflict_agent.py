# agents/conflict_agent.py
# Conflict Agent — scans Q&A for contradictions
# Flags in chat, user must acknowledge before generation

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
    add_chat_message,
)

load_dotenv()


# ── LLM Init ─────────────────────────────────────────────────────────────────

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,  # Low temp — deterministic conflict detection
    )


# ── System Prompt ─────────────────────────────────────────────────────────────

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
      "explanation": "<plain English: why this is a conflict and what it means for development>",
      "suggestion": "<one concrete suggestion to resolve this conflict>"
    }
  ],
  "total_conflicts": <int>,
  "scan_summary": "<one line: overall quality assessment of requirements>"
}
"""


# ── Build Context ─────────────────────────────────────────────────────────────

def _build_context() -> list:
    idea = get_idea()
    qa_pairs = get_qa_pairs()

    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    user_content = f"""
Scan the following product requirements for conflicts:

ORIGINAL IDEA:
{idea}

Q&A SESSION:
{qa_text}

Identify all contradictions, ambiguities, and conflicts.
Return strict JSON as specified.
"""
    return [
        SystemMessage(content=CONFLICT_SYSTEM_PROMPT),
        HumanMessage(content=user_content)
    ]


# ── Parse Response ────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback — assume no conflicts, log raw
        return {
            "conflicts": [],
            "total_conflicts": 0,
            "scan_summary": "Parse error — proceeding without conflict data"
        }


# ── Format Chat Warning ───────────────────────────────────────────────────────

def _format_conflict_message(parsed: dict) -> str:
    """
    Formats conflict results as chat message for user.
    """
    total = parsed.get("total_conflicts", 0)
    summary = parsed.get("scan_summary", "")
    conflicts = parsed.get("conflicts", [])

    if total == 0:
        return (
            f"✅ **No conflicts detected.**\n\n"
            f"_{summary}_\n\n"
            f"Proceeding to generate your documents..."
        )

    # Build warning message
    msg = f"⚠️ **{total} conflict(s) found in your requirements.**\n\n"
    msg += f"_{summary}_\n\n"
    msg += "Please review and resolve before documents are generated:\n\n"
    msg += "---\n"

    for c in conflicts:
        msg += f"**Conflict {c['id']}: {c['title']}**\n"
        msg += f"- 📌 **Source A:** {c['source_a']}\n"
        msg += f"- 📌 **Source B:** {c['source_b']}\n"
        msg += f"- ❗ **Issue:** {c['explanation']}\n"
        msg += f"- 💡 **Suggestion:** {c['suggestion']}\n"
        msg += "---\n"

    msg += (
        "\nType your clarifications below to resolve these conflicts, "
        "then type **'proceed'** when ready to generate documents."
    )

    return msg


# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_conflict_scan() -> tuple[str, bool]:
    """
    Scans all Q&A for conflicts.

    Returns:
        (chat_message: str, has_conflicts: bool)

    has_conflicts=False → caller can immediately trigger generation
    has_conflicts=True  → show message, wait for user to resolve + type 'proceed'
    """
    llm = get_llm()
    messages = _build_context()
    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)

    # Store flags in state
    set_conflict_flags(parsed.get("conflicts", []))

    # Format message for chat
    chat_msg = _format_conflict_message(parsed)
    add_chat_message("assistant", chat_msg)

    has_conflicts = parsed.get("total_conflicts", 0) > 0
    return chat_msg, has_conflicts


# ── Resolve Handler ───────────────────────────────────────────────────────────

def handle_conflict_resolution(user_input: str) -> tuple[str, bool]:
    """
    Called when user responds after conflicts shown.
    If user types 'proceed' → return ready=True
    Else → re-scan with updated context (user clarification appended)
    
    Returns:
        (response_message: str, ready_to_generate: bool)
    """
    if user_input.strip().lower() == "proceed":
        msg = "✅ Acknowledged. Generating your documents now..."
        add_chat_message("assistant", msg)
        return msg, True

    # User gave clarification — append to chat and re-scan
    add_chat_message("user", user_input)

    # Re-run scan with clarification noted
    llm = get_llm()
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    existing_flags = get_conflict_flags()

    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    flags_text = json.dumps(existing_flags, indent=2)

    messages = [
        SystemMessage(content=CONFLICT_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Original idea: {idea}

Q&A session:
{qa_text}

Previously flagged conflicts:
{flags_text}

User clarification provided:
{user_input}

Re-scan considering this clarification.
Update conflict list — remove any resolved, flag any new ones.
Return strict JSON as specified.
""")
    ]

    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)
    set_conflict_flags(parsed.get("conflicts", []))

    chat_msg = _format_conflict_message(parsed)
    add_chat_message("assistant", chat_msg)

    has_conflicts = parsed.get("total_conflicts", 0) > 0
    return chat_msg, not has_conflicts  # ready=True when no conflicts remain