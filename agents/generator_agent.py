# agents/generator_agent.py
# Generator Agent — TWO separate LLM calls
# Call 1: BRD from idea + Q&A
# Call 2: User Stories from idea + Q&A + BRD (richer context)

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
    set_generation_done,
)
from utils.error_handler import llm_call_with_retry

load_dotenv()

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
    )

# ── BRD System Prompt ─────────────────────────────────────────────────────────

BRD_SYSTEM_PROMPT = """
You are ScopeCraft's BRD Generator — an expert Business Analyst that produces
professional Business Requirements Documents.

Generate a structured BRD from the product requirements provided.

Use EXACTLY these sections in this order:

# Business Requirements Document

## 1. Problem Statement
<What problem does this product solve? Who has this problem? Why does it matter?>

## 2. Actors
| Actor | Type | Description |
|-------|------|-------------|

## 3. Functional Requirements
| ID | Requirement | Priority |
|----|-------------|----------|

## 4. Non-Functional Requirements
| ID | Requirement | Category |
|----|-------------|----------|

## 5. Scope
### In Scope
<Bullet list of what IS included>

### Out of Scope
<Bullet list of what is explicitly NOT included>

## 6. Assumptions & Constraints
<List all assumptions and constraints — include any flagged conflicts here>

## 7. Success Metrics
<Measurable KPIs — how will we know this product succeeded?>

RULES:
- Use actual product details — no generic placeholders
- Professional enough for client presentation
- Return STRICT JSON only, no extra text

RESPONSE FORMAT:
{
  "brd": "<full BRD markdown as string>",
  "brd_summary": "<two sentences: core problem solved + key actors>"
}
"""

# ── User Stories System Prompt ────────────────────────────────────────────────

STORIES_SYSTEM_PROMPT = """
You are ScopeCraft's User Stories Generator — an expert Product Manager that
produces developer-ready MoSCoW-prioritised user story backlogs.

You will receive: the original idea, Q&A session, AND the already-generated BRD.
Use the BRD as your primary reference — your stories must align with BRD scope,
actors, and functional requirements exactly.

Generate a User Story backlog using this EXACT structure:

# User Story Backlog

## MoSCoW Priority Legend
- Must Have — critical, product fails without this
- Should Have — important, include if possible
- Could Have — nice to have, include if time permits
- Won't Have — explicitly out of scope for this version

## Epics & Stories

### Epic 1: <Epic Name>
**Goal:** <what this epic achieves>

| Story ID | User Story | Acceptance Criteria | MoSCoW | Size | Effort |
|----------|------------|---------------------|--------|------|--------|
| US-001 | As a <actor>, I want to <action> so that <benefit> | <testable criteria> | Must Have | M | 2-3 days |

**Epic Effort Total:** ~X days

<Size key: XS=half day, S=1 day, M=2-3 days, L=1 week, XL=2+ weeks>

EFFORT SIZING RULES:
- XS: Simple UI change, config update, copy change
- S: Single form, basic CRUD endpoint, simple validation
- M: Feature with frontend + backend + DB + tests
- L: Complex feature, third-party integration, auth flow
- XL: New subsystem, major architecture change, ML component
- Size every single story — no blanks
- Add effort summary at bottom of each epic

## Summary
| Priority | Count | Est. Effort |
|----------|-------|-------------|
| Must Have | X | X days |
| Should Have | X | X days |
| Could Have | X | X days |
| Won't Have | X | — |
| **Total** | **X** | **X days** |

## Effort Overview
| Size | Count | Days Each | Total Days |
|------|-------|-----------|------------|
| XS | X | 0.5 | X |
| S | X | 1 | X |
| M | X | 2.5 | X |
| L | X | 5 | X |
| XL | X | 10 | X |
| **Total** | **X** | — | **X days** |

RULES:
- Actors must match BRD actors exactly
- Story scope must stay within BRD In Scope section
- Every story needs testable acceptance criteria
- Size column: XS / S / M / L / XL
- Return STRICT JSON only

RESPONSE FORMAT:
{
  "user_stories": "<full User Stories markdown as string>",
  "stories_summary": "<one line: total stories + priority breakdown>"
}
"""

# ── Build Contexts ────────────────────────────────────────────────────────────

def _build_brd_context(idea: str, qa_pairs: list, conflict_flags: list) -> list:
    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    conflict_text = "None detected."
    if conflict_flags:
        conflict_text = ""
        for c in conflict_flags:
            conflict_text += (
                f"\n- {c.get('title','')}: {c.get('explanation','')}"
                f" | Suggestion: {c.get('suggestion','')}\n"
            )

    return [
        SystemMessage(content=BRD_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate BRD from these requirements:

ORIGINAL IDEA:
{idea}

REQUIREMENTS Q&A:
{qa_text}

KNOWN CONFLICTS:
{conflict_text}

Return strict JSON only.
""")
    ]

def _build_stories_context(idea: str, qa_pairs: list, conflict_flags: list, brd: str) -> list:
    qa_text = ""
    for i, pair in enumerate(qa_pairs):
        qa_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}\n"

    conflict_text = "None detected."
    if conflict_flags:
        conflict_text = ""
        for c in conflict_flags:
            conflict_text += f"\n- {c.get('title','')}: {c.get('explanation','')}\n"

    return [
        SystemMessage(content=STORIES_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate User Stories aligned to the BRD below:

ORIGINAL IDEA:
{idea}

REQUIREMENTS Q&A:
{qa_text}

KNOWN CONFLICTS:
{conflict_text}

GENERATED BRD (use as primary reference):
{brd}

Return strict JSON only.
""")
    ]

# ── Parse Responses ───────────────────────────────────────────────────────────

def _parse_brd_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "brd": raw,
            "brd_summary": "Parse error on BRD generation"
        }

def _parse_stories_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "user_stories": raw,
            "stories_summary": "Parse error on Stories generation"
        }

# ── Main Entry Point ──────────────────────────────────────────────────────────

def run_generation(idea: str, qa_pairs: list, conflict_flags: list) -> tuple:
    """
    TWO sequential LLM calls:
    1. Generate BRD
    2. Generate User Stories using BRD as context

    Returns (brd: str, user_stories: str)
    """
    llm = get_llm()

    # ── CALL 1: BRD ──────────────────────────────────────────────────────────
    brd_messages = _build_brd_context(idea, qa_pairs, conflict_flags)
    brd_raw = llm_call_with_retry(llm.invoke, brd_messages).content
    brd_parsed = _parse_brd_response(brd_raw)
    brd = brd_parsed.get("brd", "")

    # Save BRD immediately — visible even if stories fail
    set_brd(brd)

    # ── CALL 2: USER STORIES (uses BRD as input) ──────────────────────────────
    stories_messages = _build_stories_context(idea, qa_pairs, conflict_flags, brd)
    stories_raw = llm_call_with_retry(llm.invoke, stories_messages).content
    stories_parsed = _parse_stories_response(stories_raw)
    stories = stories_parsed.get("user_stories", "")

    set_user_stories(stories)
    set_generation_done(True)

    return brd, stories