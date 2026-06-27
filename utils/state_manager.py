# utils/state_manager.py
# Session state manager for ScopeCraft
# Single-session now — DB persistence ready for future

import streamlit as st


# ── Keys ────────────────────────────────────────────────────────────────────

STATE_KEYS = {
    "idea": None,                  # Raw user idea (str)
    "qa_pairs": [],                # List of {"question": str, "answer": str}
    "chat_history": [],            # List of {"role": "user"|"assistant", "content": str}
    "conflict_flags": [],          # List of {"conflict": str, "explanation": str}
    "brd": None,                   # Generated BRD markdown (str)
    "user_stories": None,          # Generated User Stories markdown (str)
    "interview_complete": False,   # Flag: interview done, trigger generation
    "question_count": 0,           # Track how many questions asked (max 10)
    "completeness_score": 0,       # 0–100, generation triggers at 80+
    "generation_done": False,      # Flag: BRD + stories generated
}


# ── Init ─────────────────────────────────────────────────────────────────────

def init_state():
    """
    Call once at app.py startup.
    Sets all keys in st.session_state if not already present.
    Safe to call on every rerun — won't overwrite existing values.
    """
    for key, default in STATE_KEYS.items():
        if key not in st.session_state:
            # Deep copy lists so each session gets own list, not shared ref
            if isinstance(default, list):
                st.session_state[key] = []
            else:
                st.session_state[key] = default


# ── Reset ────────────────────────────────────────────────────────────────────

def reset_state():
    """
    Full session reset. Bound to Reset button in UI.
    Future: before reset, persist to DB here.
    """
    for key, default in STATE_KEYS.items():
        if isinstance(default, list):
            st.session_state[key] = []
        else:
            st.session_state[key] = default


# ── Q&A ──────────────────────────────────────────────────────────────────────

def add_qa_pair(question: str, answer: str):
    """Append one Q&A exchange to history."""
    st.session_state["qa_pairs"].append({
        "question": question,
        "answer": answer
    })


def get_qa_pairs() -> list:
    """Return all Q&A pairs collected so far."""
    return st.session_state["qa_pairs"]


# ── Chat History ─────────────────────────────────────────────────────────────

def add_chat_message(role: str, content: str):
    """
    role: 'user' or 'assistant'
    Appends to chat_history — used by Streamlit chat UI.
    """
    st.session_state["chat_history"].append({
        "role": role,
        "content": content
    })


def get_chat_history() -> list:
    """Return full chat history for UI render."""
    return st.session_state["chat_history"]


# ── Conflicts ────────────────────────────────────────────────────────────────

def set_conflict_flags(flags: list):
    """Store conflict flags from Conflict Agent."""
    st.session_state["conflict_flags"] = flags


def get_conflict_flags() -> list:
    return st.session_state["conflict_flags"]


# ── Outputs ──────────────────────────────────────────────────────────────────

def set_brd(brd_markdown: str):
    st.session_state["brd"] = brd_markdown


def get_brd() -> str:
    return st.session_state["brd"]


def set_user_stories(stories_markdown: str):
    st.session_state["user_stories"] = stories_markdown


def get_user_stories() -> str:
    return st.session_state["user_stories"]


# ── Counters & Flags ─────────────────────────────────────────────────────────

def increment_question_count():
    st.session_state["question_count"] += 1


def get_question_count() -> int:
    return st.session_state["question_count"]


def set_completeness_score(score: int):
    st.session_state["completeness_score"] = score


def get_completeness_score() -> int:
    return st.session_state["completeness_score"]


def mark_interview_complete():
    st.session_state["interview_complete"] = True


def is_interview_complete() -> bool:
    return st.session_state["interview_complete"]


def mark_generation_done():
    st.session_state["generation_done"] = True


def is_generation_done() -> bool:
    return st.session_state["generation_done"]


def set_idea(idea_text: str):
    st.session_state["idea"] = idea_text


def get_idea() -> str:
    return st.session_state["idea"]