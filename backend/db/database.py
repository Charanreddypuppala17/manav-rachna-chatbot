import os
import json
from datetime import datetime
from typing import Optional

# Check if PostgreSQL URL is provided in the environment
DATABASE_URL = os.getenv("DATABASE_URL")
IS_POSTGRES = DATABASE_URL is not None and (
    DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")
)

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras
    print("Database: Using PostgreSQL (Production Mode)")
else:
    import sqlite3
    print("Database: Using SQLite (Local Development Mode)")

def get_connection():
    if IS_POSTGRES:
        # Connect to PostgreSQL
        # Render database URLs sometimes start with postgres://, which is fully compatible
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
        return conn
    else:
        # Connect to local SQLite database
        db_path = os.path.join(os.path.dirname(__file__), "local_supabase.db")
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(cursor, query: str, params=()):
    """Helper to convert sqlite ? placeholders to %s placeholders for PostgreSQL."""
    if IS_POSTGRES:
        query = query.replace("?", "%s")
    cursor.execute(query, params)
    return cursor

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    if IS_POSTGRES:
        # Create tables using PostgreSQL schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                sources TEXT, -- Store sources as text (JSON string)
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # Create tables using SQLite schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                title TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions (session_id) ON DELETE CASCADE
            )
        """)
        
    conn.commit()
    conn.close()
    print("Database tables initialized successfully")

# User Helpers
def create_user(email: str, password_hash: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if IS_POSTGRES:
            cursor.execute("""
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id
            """, (email.lower().strip(), password_hash))
            user_id = cursor.fetchone()["id"]
        else:
            cursor.execute("""
                INSERT INTO users (email, password_hash)
                VALUES (?, ?)
            """, (email.lower().strip(), password_hash))
            user_id = cursor.lastrowid
            
        conn.commit()
        return user_id
    finally:
        conn.close()

def get_user_by_email(email: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, "SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, "SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# Session Helpers
def create_chat_session(session_id: str, user_id: Optional[int], title: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, """
            INSERT INTO chat_sessions (session_id, user_id, title)
            VALUES (?, ?, ?)
        """, (session_id, user_id, title))
        conn.commit()
    finally:
        conn.close()

def get_chat_sessions_for_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, """
            SELECT session_id, title, created_at FROM chat_sessions
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_chat_session(session_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, "SELECT * FROM chat_sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def update_chat_session_title(session_id: str, title: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, """
            UPDATE chat_sessions SET title = ? WHERE session_id = ?
        """, (title, session_id))
        conn.commit()
    finally:
        conn.close()

def delete_chat_session(session_id: str, user_id: Optional[int]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verify ownership first
        if user_id is not None:
            execute_query(cursor, "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id = ?", (session_id, user_id))
        else:
            execute_query(cursor, "SELECT 1 FROM chat_sessions WHERE session_id = ? AND user_id IS NULL", (session_id,))
            
        if not cursor.fetchone():
            return False
            
        execute_query(cursor, "DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        return True
    finally:
        conn.close()

# Message Helpers
def save_message(session_id: str, role: str, message: str, sources: list = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sources_json = json.dumps(sources) if sources else None
        execute_query(cursor, """
            INSERT INTO messages (session_id, role, content, sources)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, message, sources_json))
        conn.commit()
    finally:
        conn.close()

def get_history(session_id: str, limit: int = 15):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, """
            SELECT role, content, sources FROM messages
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        
        history = []
        for r in reversed(rows):
            sources_list = []
            if r["sources"]:
                try:
                    sources_list = json.loads(r["sources"])
                except Exception:
                    pass
            history.append({
                "role": r["role"],
                "content": r["content"],
                "sources": sources_list
            })
        return history
    finally:
        conn.close()

def clear_history(session_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        execute_query(cursor, "DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()