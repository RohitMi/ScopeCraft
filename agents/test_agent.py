# agents/test_agent.py
# Test Agent — generates Gherkin acceptance tests from User Stories

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
        temperature=0.2,
    )

TEST_SYSTEM_PROMPT = """
You are ScopeCraft's Test Agent — a senior QA Engineer that writes
Gherkin acceptance test scenarios from user stories.

YOUR ROLE:
- Read each user story and its acceptance criteria
- Write Gherkin scenarios (Given/When/Then) for each story
- Cover: happy path, edge cases, failure cases
- Group by Epic
- Must Have stories get minimum 3 scenarios
- Should Have stories get minimum 2 scenarios
- Could Have stories get minimum 1 scenario

GHERKIN FORMAT:
Feature: <Epic Name>

  Scenario: <scenario title>
    Given <initial context>
    When <action taken>
    Then <expected outcome>

  Scenario Outline: <parameterised scenario>
    Given <context with <param>>
    When <action with <param>>
    Then <outcome with <param>>
    Examples:
      | param |
      | value1 |
      | value2 |

RULES:
- Use actual product details — no generic placeholders
- Scenarios must be testable by a QA engineer
- Each story ID must appear as a comment above its scenarios: # US-001
- Cover negative paths (what happens when input is invalid, user unauthorised etc)
- Return STRICT JSON only

RESPONSE FORMAT:
{
  "test_suites": "<full Gherkin markdown as string>",
  "test_summary": "<one line: total features, scenarios, stories covered>"
}
"""

def _build_context(user_stories: str, brd: str) -> list:
    return [
        SystemMessage(content=TEST_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate Gherkin acceptance test scenarios from these user stories:

BRD CONTEXT (for domain understanding):
{brd}

USER STORIES:
{user_stories}

Write comprehensive Gherkin scenarios for every story.
Return strict JSON only.
""")
    ]

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "test_suites": raw,
            "test_summary": "Parse error on test generation"
        }

def run_test_generation() -> str:
    """
    Generates Gherkin acceptance tests from stored User Stories + BRD.
    Returns test_suites markdown string.
    """
    llm = get_llm()
    user_stories = get_user_stories()
    brd = get_brd()

    if not user_stories:
        return "⚠️ No user stories found — generate documents first."

    messages = _build_context(user_stories, brd)
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)
    return parsed.get("test_suites", "")