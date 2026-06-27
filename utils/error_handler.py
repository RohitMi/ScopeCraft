# utils/error_handler.py
# Retry wrapper + error state helpers for all agent LLM calls

import time
import streamlit as st

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds between retries

def llm_call_with_retry(fn, *args, **kwargs):
    """
    Wraps any LLM call function with retry logic.
    Shows attempt count in UI.
    On all retries exhausted — sets error in session state.
    
    Usage:
        result = llm_call_with_retry(llm.invoke, messages)
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    # All retries exhausted — store error for UI
    set_last_error(str(last_error))
    raise last_error


def set_last_error(msg: str):
    st.session_state['last_error'] = msg
    st.session_state['has_error'] = True

def clear_error():
    st.session_state['last_error'] = ''
    st.session_state['has_error'] = False

def get_last_error() -> str:
    return st.session_state.get('last_error', '')

def has_error() -> bool:
    return st.session_state.get('has_error', False)