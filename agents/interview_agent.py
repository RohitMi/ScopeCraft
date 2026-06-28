# agents/interview_agent.py
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
import os
import json

from utils.state_manager import (
    get_qa_pairs, set_qa_pairs,
    get_idea,
    get_question_count, set_question_count,
    get_completeness, set_completeness,
    get_chat_history,
)
from utils.error_handler import llm_call_with_retry

load_dotenv()

def get_llm():
    return ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model_name="llama-3.3-70b-versatile",
        temperature=0.4,
    )

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
"""

def _build_context(is_first: bool, latest_answer: str = None) -> list:
    idea = get_idea()
    qa_pairs = get_qa_pairs()
    q_count = get_question_count()
    score = get_completeness()

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

def _parse_response(raw: str) -> dict:
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "type": "question",
            "message": raw.strip(),
            "completeness_score": get_completeness(),
            "reasoning": "parse error — using raw response"
        }

def start_interview(idea: str) -> str:
    llm = get_llm()
    messages = _build_context(is_first=True)
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)
    set_completeness(parsed.get("completeness_score", 0))
    set_question_count(1)
    return parsed["message"]

def process_answer(user_answer: str) -> dict:
    from utils.validators import validate_answer
    is_valid, err_msg = validate_answer(user_answer)
    if not is_valid:
        return {
            "message":      f"⚠️ {err_msg} Please try again.",
            "completeness": get_completeness(),
            "done":         False,
            "qa_pair":      None,
        }

    llm = get_llm()
    q_count = get_question_count()

    # Get last assistant message = question being answered
    history = get_chat_history()
    last_question = ""
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_question = msg["content"]
            break

    # Save Q&A pair
    qa_pairs = get_qa_pairs()
    qa_pair = {"question": last_question, "answer": user_answer}
    qa_pairs.append(qa_pair)
    set_qa_pairs(qa_pairs)

    # Call LLM
    messages = _build_context(is_first=False, latest_answer=user_answer)
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)

    new_score = parsed.get("completeness_score", get_completeness())
    set_completeness(new_score)

    done = False
    response_msg = parsed["message"]

    if parsed["type"] == "complete" and q_count >= 5:
        done = True
    elif parsed["type"] == "complete" and q_count < 5:
        response_msg = _force_next_question(user_answer)

    set_question_count(q_count + 1)

    return {
        "message":      response_msg,
        "completeness": new_score,
        "done":         done,
        "qa_pair":      qa_pair,
    }

def _force_next_question(latest_answer: str) -> str:
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
    raw = llm_call_with_retry(llm.invoke, messages).content
    parsed = _parse_response(raw)
    return parsed["message"]