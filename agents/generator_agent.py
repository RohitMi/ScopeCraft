# agents/generator_agent.py
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

# User Story Backlog

## MoSCoW Priority Legend
- Must Have — critical, product fails without this
- Should Have — important, include if possible
- Could Have — nice to have, include if time permits
- Won't Have — explicitly out of scope for this version

## Epics & Stories

### Epic 1: <Epic Name>
**Goal:** <what this epic achieves>

| Story ID | User Story | Acceptance Criteria | MoSCoW |
|----------|------------|---------------------|--------|
| US-001 | As a <actor>, I want to <action> so that <benefit> | <testable criteria> | Must Have |

## Summary
| Priority | Count |
|----------|-------|
| Must Have | X |
| Should Have | X |
| Could Have | X |
| Won't Have | X |
| **Total** | **X** |

---

RULES:
- Be specific — use actual product details, not generic placeholders
- BRD professional enough for client presentation
- Stories specific enough for developer to start coding
- If conflicts flagged, note in Assumptions & Constraints
- Return STRICT JSON only

RESPONSE FORMAT:
{
  "brd": "<full BRD markdown>",
  "user_stories": "<full User Stories markdown>",
  "generation_summary": "<one line summary>"
}
"""

def _build_context(idea: str, qa_pairs: list, conflict_flags: list) -> list:
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
        SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate BRD and User Stories from these requirements:

ORIGINAL IDEA:
{idea}

REQUIREMENTS Q&A:
{qa_text}

KNOWN CONFLICTS:
{conflict_text}

Return strict JSON only.
""")
    ]

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "brd": raw,
            "user_stories": "Generation error — please retry.",
            "generation_summary": "Parse error"
        }

def run_generation(idea: str, qa_pairs: list, conflict_flags: list) -> tuple:
    llm = get_llm()
    messages = _build_context(idea, qa_pairs, conflict_flags)
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)

    brd = parsed.get("brd", "")
    stories = parsed.get("user_stories", "")

    set_brd(brd)
    set_user_stories(stories)
    set_generation_done(True)

    return brd, stories