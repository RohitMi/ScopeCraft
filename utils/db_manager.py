import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'scopecraft.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create sessions table if not exists."""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            idea        TEXT,
            qa_pairs    TEXT,
            chat_history TEXT,
            conflict_flags TEXT,
            brd         TEXT,
            user_stories TEXT,
            created_at  TEXT,
            updated_at  TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_session(name: str, state: dict, session_id: int = None) -> int:
    """Insert or update a session. Returns session_id."""
    conn = get_connection()
    now = datetime.now().isoformat()

    data = {
        'name':           name,
        'idea':           state.get('idea', ''),
        'qa_pairs':       json.dumps(state.get('qa_pairs', [])),
        'chat_history':   json.dumps(state.get('chat_history', [])),
        'conflict_flags': json.dumps(state.get('conflict_flags', [])),
        'brd':            state.get('brd', ''),
        'user_stories':   state.get('user_stories', ''),
        'updated_at':     now
    }

    if session_id:
        conn.execute('''
            UPDATE sessions SET
                name=:name, idea=:idea, qa_pairs=:qa_pairs,
                chat_history=:chat_history, conflict_flags=:conflict_flags,
                brd=:brd, user_stories=:user_stories, updated_at=:updated_at
            WHERE id=:id
        ''', {**data, 'id': session_id})
        conn.commit()
        conn.close()
        return session_id
    else:
        data['created_at'] = now
        cur = conn.execute('''
            INSERT INTO sessions
                (name, idea, qa_pairs, chat_history, conflict_flags, brd, user_stories, created_at, updated_at)
            VALUES
                (:name, :idea, :qa_pairs, :chat_history, :conflict_flags, :brd, :user_stories, :created_at, :updated_at)
        ''', data)
        conn.commit()
        new_id = cur.lastrowid
        conn.close()
        return new_id

def load_session(session_id: int) -> dict:
    """Load session by ID. Returns state dict."""
    conn = get_connection()
    row = conn.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        'idea':           row['idea'],
        'qa_pairs':       json.loads(row['qa_pairs'] or '[]'),
        'chat_history':   json.loads(row['chat_history'] or '[]'),
        'conflict_flags': json.loads(row['conflict_flags'] or '[]'),
        'brd':            row['brd'] or '',
        'user_stories':   row['user_stories'] or '',
        'session_name':   row['name'],
        'session_id':     row['id']
    }

def list_sessions() -> list:
    """Return all sessions ordered by latest update."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT id, name, idea, updated_at FROM sessions ORDER BY updated_at DESC'
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_session(session_id: int):
    """Delete session by ID."""
    conn = get_connection()
    conn.execute('DELETE FROM sessions WHERE id=?', (session_id,))
    conn.commit()
    conn.close()