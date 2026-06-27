# agents/generator_agent.py
# Generator Agent — produces BRD + User Stories in single LLM call
# BRD: fixed structure | User Stories: MoSCoW prioritised

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json

from utils.state_manager import (
    get_idea,
    get_qa_pairs,
    get_conflict_flags,
    set_brd,
    set_user_stories,
    mark_generation_done,
    add_chat_message,
)

load_dotenv()


# ── LLM Init ─────────────────────────────────────────────────────────────────

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
    )


# ── System Prompt ─────────────────────────────────────────────────────────────

GENERATOR_SYSTEM_PROMPT = """
You are ScopeCraft's Generator Agent — an expert Business Analyst and 
Product Manager that produces professional software development artifacts.

YOUR ROLE:
Generate TWO documents from the product requirements provided:
1. A structured Business Requirements Document (BRD)
2. A prioritised User Story backlog using MoSCoW method

DOCUMENT 1 — BRD (fixed structure, markdown):
Use EXACTLY these sections in this order:

# Business Requirements Document

## 1. Problem Statement
<What problem does this product solve? Who has this problem? Why does it matter?>

## 2. Actors
<All users, systems, and external entities that interact with the product>
| Actor | Type | Description |
|-------|------|-------------|

## 3. Functional Requirements
<Numbered list of what the system must do>
| ID | Requirement | Priority |
|----|-------------|----------|

## 4. Non-Functional Requirements
<Performance, security, scalability, usability constraints>
| ID | Requirement | Category |
|----|-------------|----------|

## 5. Scope
### In Scope
<Bullet list of what IS included in this product>

### Out of Scope
<Bullet list of what is explicitly NOT included>

## 6. Assumptions & Constraints
<List all assumptions made and constraints identified>

## 7. Success Metrics
<How will we know this product succeeded? Measurable KPIs>

---

DOCUMENT 2 — USER STORIES (MoSCoW, markdown):
Use EXACTLY this structure:

# User Story Backlog

## MoSCoW Priority Legend
- 🔴 Must Have — critical, product fails without this
- 🟡 Should Have — important, include if possible
- 🟢 Could Have — nice to have, include if time permits
- ⚪ Won't Have — explicitly out of scope for this version

## Epics & Stories

### Epic 1: <Epic Name>
**Goal:** <what this epic achieves>

| Story ID | User Story | Acceptance Criteria | MoSCoW |
|----------|------------|--------------------| -------|
| US-001 | As a <actor>, I want to <action> so that <benefit> | <testable criteria> | 🔴 Must Have |

<repeat for each epic>

## Summary
| Priority | Count |
|----------|-------|
| 🔴 Must Have | X |
| 🟡 Should Have | X |
| 🟢 Could Have | X |
| ⚪ Won't Have | X |
| **Total** | **X** |

---

RULES:
- Be specific — use actual product details from requirements, not generic placeholders
- BRD must be professional enough for a client presentation
- User stories must be specific enough for a developer to start coding
- If conflicts were flagged, note them in Assumptions & Constraints section
- Return STRICT JSON only — no extra text outside JSON

RESPONSE FORMAT:
{
  "brd": "<full BRD markdown as string>",
  "user_stories": "<full User Stories markdown as string>",
  "generation_summary": "<one line: what was generated and key highlights>"
}
"""


# ── Build Context ─────────────────────────────────────────────────────────────

def _build_context() -> list:
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    conflict_flags = get_conflict_flags()

    # Q&A history
    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    # Conflict summary
    conflict_text = "None detected."
    if conflict_flags:
        conflict_text = ""
        for c in conflict_flags:
            conflict_text += (
                f"\n- Conflict: {c.get('title', '')}\n"
                f"  Issue: {c.get('explanation', '')}\n"
                f"  Suggestion: {c.get('suggestion', '')}\n"
            )

    user_content = f"""
Generate BRD and User Stories from these requirements:

ORIGINAL IDEA:
{idea}

REQUIREMENTS Q&A:
{qa_text}

KNOWN CONFLICTS / RESOLUTIONS:
{conflict_text}

Produce both documents now. Return strict JSON only.
"""
    return [
        SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=user_content)
    ]


# ── Parse Response ────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback — return raw as BRD, empty stories
        return {
            "brd": raw,
            "user_stories": "⚠️ Generation error — please retry.",
            "generation_summary": "Parse error on generation output"
        }


# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_generation() -> tuple[str, str]:
    """
    Single LLM call — generates BRD + User Stories.

    Returns:
        (brd_markdown: str, user_stories_markdown: str)

    Also:
        - Saves both to session state
        - Marks generation done
        - Adds completion message to chat
    """
    llm = get_llm()
    messages = _build_context()

    # Notify state — generation starting
    add_chat_message(
        "assistant",
        "⚙️ Generating your Business Requirements Document and User Story Backlog..."
    )

    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)

    brd = parsed.get("brd", "")
    stories = parsed.get("user_stories", "")
    summary = parsed.get("generation_summary", "")

    # Persist to state
    set_brd(brd)
    set_user_stories(stories)
    mark_generation_done()

    # Completion message in chat
    completion_msg = (
        f"✅ **Documents generated successfully!**\n\n"
        f"_{summary}_\n\n"
        f"Switch to the **📄 BRD** or **📋 User Stories** tabs above to view your documents."
    )
    add_chat_message("assistant", completion_msg)

    return brd, stories