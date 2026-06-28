import streamlit as st
from utils.db_manager import save_session, load_session

def init_state():
    """Initialise all session state keys if not present."""
    defaults = {
        'phase':           'landing',
        'idea':            '',
        'qa_pairs':        [],
        'chat_history':    [],
        'conflict_flags':  [],
        'brd':             '',
        'user_stories':    '',
        'question_count':  0,
        'completeness':    0,
        'generation_done': False,
        'conflict_done':   False,
        'session_id':      None,
        'session_name':    '',
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def reset_state():
    """Full wipe — back to landing."""
    keys = [
        'phase', 'idea', 'qa_pairs', 'chat_history', 'conflict_flags',
        'brd', 'user_stories', 'question_count', 'completeness',
        'generation_done', 'conflict_done', 'session_id', 'session_name',
        'acceptance_tests', 'hld'
    ]
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]
    init_state()

# --- Getters ---
def get_phase():           return st.session_state.get('phase', 'landing')
def get_idea():            return st.session_state.get('idea', '')
def get_qa_pairs():        return st.session_state.get('qa_pairs', [])
def get_chat_history():    return st.session_state.get('chat_history', [])
def get_conflict_flags():  return st.session_state.get('conflict_flags', [])
def get_brd():             return st.session_state.get('brd', '')
def get_user_stories():    return st.session_state.get('user_stories', '')
def get_question_count():  return st.session_state.get('question_count', 0)
def get_completeness():    return st.session_state.get('completeness', 0)
def is_generation_done():  return st.session_state.get('generation_done', False)
def is_conflict_done():    return st.session_state.get('conflict_done', False)
def get_session_id():      return st.session_state.get('session_id', None)
def get_session_name():    return st.session_state.get('session_name', '')

# --- Setters ---
def set_phase(v):          st.session_state['phase'] = v
def set_idea(v):           st.session_state['idea'] = v
def set_qa_pairs(v):       st.session_state['qa_pairs'] = v
def set_chat_history(v):   st.session_state['chat_history'] = v
def set_conflict_flags(v): st.session_state['conflict_flags'] = v
def set_brd(v):            st.session_state['brd'] = v
def set_user_stories(v):   st.session_state['user_stories'] = v
def set_question_count(v): st.session_state['question_count'] = v
def set_completeness(v):   st.session_state['completeness'] = v
def set_generation_done(v):st.session_state['generation_done'] = v
def set_conflict_done(v):  st.session_state['conflict_done'] = v
def set_session_id(v):     st.session_state['session_id'] = v
def set_session_name(v):   st.session_state['session_name'] = v

# --- Persistence helpers ---

def _build_state_snapshot() -> dict:
    return {
        'idea':           get_idea(),
        'qa_pairs':       get_qa_pairs(),
        'chat_history':   get_chat_history(),
        'conflict_flags': get_conflict_flags(),
        'brd':            get_brd(),
        'user_stories':   get_user_stories(),
    }

def save_current_session(name: str = None) -> int:
    session_name = name or get_session_name() or 'Untitled Session'
    set_session_name(session_name)
    snapshot = _build_state_snapshot()
    sid = save_session(
        name=session_name,
        state=snapshot,
        session_id=get_session_id()
    )
    set_session_id(sid)
    return sid

def load_session_into_state(session_id: int) -> bool:
    data = load_session(session_id)
    if not data:
        return False

    reset_state()

    set_idea(data['idea'])
    set_qa_pairs(data['qa_pairs'])
    set_chat_history(data['chat_history'])
    set_conflict_flags(data['conflict_flags'])
    set_brd(data['brd'])
    set_user_stories(data['user_stories'])
    set_session_id(data['session_id'])
    set_session_name(data['session_name'])

    if data['brd']:
        set_phase('done')
        set_generation_done(True)
        set_conflict_done(True)
    elif data['conflict_flags']:
        set_phase('conflict')
    elif data['chat_history']:
        set_phase('interview')
    else:
        set_phase('landing')

    return True