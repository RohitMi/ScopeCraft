# agents/interview_agent.py
# Interview Agent — drives clarifying Q&A with user
# LLM-scored completeness, min 5 questions, max 10

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json

from utils.state_manager import (
    add_qa_pair,
    add_chat_message,
    get_qa_pairs,
    get_idea,
    increment_question_count,
    get_question_count,
    set_completeness_score,
    get_completeness_score,
    mark_interview_complete,
    is_interview_complete,
)

load_dotenv()

# ── LLM Init ─────────────────────────────────────────────────────────────────

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.4,
    )


# ── System Prompt ─────────────────────────────────────────────────────────────

INTERVIEW_SYSTEM_PROMPT = """
You are ScopeCraft's Interview Agent — an expert Business Analyst conducting 
a structured requirements gathering session for a software product idea.

YOUR ROLE:
- Ask targeted, specific clarifying questions to extract requirements
- Questions must be dynamic — tailored to the specific idea given
- Cover areas relevant to the idea: actors, goals, constraints, scope, 
  tech preferences, target users, integrations, monetization, edge cases
- One question per response — never ask multiple questions at once

COMPLETENESS SCORING:
- After each answer, internally assess how complete the requirements picture is
- Score 0–100 based on: clarity of goal, known actors, defined scope, 
  constraints identified, technical direction, edge cases surfaced
- Return score honestly — do not inflate

RULES:
- Minimum 5 questions must be asked before generation can trigger
- Maximum 10 questions total
- Trigger generation when: score >= 80 AND questions_asked >= 5
- OR trigger when: questions_asked >= 10 (regardless of score)
- Never repeat a question already asked
- Stay focused on the product idea — no small talk

RESPONSE FORMAT (strict JSON only, no markdown, no extra text):
{
  "type": "question" | "complete",
  "message": "<acknowledgement if first> + <single question OR completion message>",
  "completeness_score": <int 0-100>,
  "reasoning": "<one line: why this score>"
}

- type "question": more info needed, continue interview
- type "complete": requirements sufficient, ready to generate documents
"""


# ── Build Context for LLM ────────────────────────────────────────────────────

def _build_context(is_first: bool, latest_answer: str = None) -> list:
    """
    Build message list for LLM call.
    Includes idea + full Q&A history for context.
    """
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    q_count = get_question_count()
    score = get_completeness_score()

    # Build history summary
    history_text = ""
    for i, pair in enumerate(qa_pairs):
        history_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}"

    if is_first:
        user_content = f"""
New product idea submitted:

IDEA: {idea}

Questions asked so far: 0
Current completeness score: 0

This is the FIRST interaction. 
Respond with a brief acknowledgement of the idea (1-2 sentences), 
then ask your first targeted clarifying question.
"""
    else:
        user_content = f"""
Product idea: {idea}

Q&A history so far:
{history_text}

Latest answer just given: {latest_answer}

Questions asked so far: {q_count}
Current completeness score: {score}

Assess the latest answer, update completeness score, 
then decide: ask next question OR mark complete.
Remember: minimum 5 questions before marking complete.
"""

    return [
        SystemMessage(content=INTERVIEW_SYSTEM_PROMPT),
        HumanMessage(content=user_content)
    ]


# ── Parse LLM Response ───────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    """
    Parse JSON from LLM response.
    Fallback if LLM returns malformed JSON.
    """
    try:
        # Strip any accidental markdown fences
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback — treat as question, ask to clarify
        return {
            "type": "question",
            "message": raw.strip(),
            "completeness_score": get_completeness_score(),
            "reasoning": "parse error — using raw response"
        }


# ── Main Entry Points ────────────────────────────────────────────────────────

def start_interview() -> str:
    """
    Called when user submits idea for first time.
    Returns acknowledgement + first question as string.
    """
    llm = get_llm()
    messages = _build_context(is_first=True)
    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)

    # Update state
    set_completeness_score(parsed.get("completeness_score", 0))

    # Store first question in chat history
    add_chat_message("assistant", parsed["message"])

    # Track question count (first question embedded in ack message)
    increment_question_count()

    return parsed["message"]


def process_answer(user_answer: str) -> tuple[str, bool]:
    """
    Called each time user submits an answer during interview.
    
    Returns:
        (response_message: str, interview_done: bool)
    
    interview_done=True means: trigger Conflict Agent + Generator Agent
    """
    llm = get_llm()
    q_count = get_question_count()

    # Store this answer paired with last question
    qa_pairs = get_qa_pairs()
    last_question = ""
    if qa_pairs:
        last_question = qa_pairs[-1]["question"] if qa_pairs else ""

    # Get last assistant message as the question being answered
    # Find last question from chat history
    from utils.state_manager import get_chat_history
    history = get_chat_history()
    last_q_msg = ""
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_q_msg = msg["content"]
            break

    # Save Q&A pair
    add_qa_pair(last_q_msg, user_answer)
    add_chat_message("user", user_answer)

    # Build context and call LLM
    messages = _build_context(is_first=False, latest_answer=user_answer)
    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)

    # Update score
    new_score = parsed.get("completeness_score", get_completeness_score())
    set_completeness_score(new_score)

    response_msg = parsed["message"]
    interview_done = False

    if parsed["type"] == "complete":
        # Double-check min 5 questions enforced
        if q_count >= 5:
            mark_interview_complete()
            interview_done = True
        else:
            # Force another question — min not met
            response_msg = _force_next_question(user_answer)
            increment_question_count()
    else:
        increment_question_count()

    add_chat_message("assistant", response_msg)
    return response_msg, interview_done


def _force_next_question(latest_answer: str) -> str:
    """
    LLM tried to complete before min 5 questions.
    Force one more targeted question.
    """
    llm = get_llm()
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    q_count = get_question_count()

    history_text = ""
    for i, pair in enumerate(qa_pairs):
        history_text += f"\nQ{i+1}: {pair['question']}\nA{i+1}: {pair['answer']}"

    messages = [
        SystemMessage(content=INTERVIEW_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Product idea: {idea}

Q&A so far:
{history_text}

You attempted to mark complete but minimum 5 questions not yet reached.
Questions asked: {q_count}

Ask one more specific clarifying question. 
Still respond in strict JSON format with type: "question".
""")
    ]

    raw = llm.invoke(messages).content
    parsed = _parse_response(raw)
    return parsed["message"]