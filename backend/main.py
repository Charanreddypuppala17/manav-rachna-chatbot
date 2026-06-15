import os
import sys
print("DIAGNOSTIC - Environment keys:", list(os.environ.keys()))
print("DIAGNOSTIC - GROQ_API_KEY exists:", "GROQ_API_KEY" in os.environ)

from uuid import uuid4
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, status, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Make sure backend/ is in path
sys.path.append(os.path.dirname(__file__))

# Pre-load embedding model during startup to prevent request timeouts on Render
try:
    print("Pre-loading RAG search modules (Initializing Qdrant client)...")
    from rag.search import search
    print("RAG search modules pre-loaded successfully!")
except Exception as e:
    print(f"Warning: RAG search pre-load failed: {e}")

from api.chat import chat
from api.auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_user_optional, verify_google_token
import db.database as db

app = FastAPI(title="College Chatbot API")

# Allow frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    token: str

class Message(BaseModel):
    role: str
    content: str
    sources: Optional[List[str]] = []

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    model_used: str
    session_id: str

@app.on_event("startup")
async def startup():
    db.init_db()

@app.get("/")
def root():
    return {"status": "College Chatbot API is running"}

# Authentication Endpoints
@app.post("/api/auth/register")
def register(user: UserRegister):
    existing_user = db.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    password_hash = get_password_hash(user.password)
    try:
        db.create_user(user.email, password_hash)
        return {"message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/api/auth/login")
def login(user: UserLogin):
    db_user = db.get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    token = create_access_token(data={"sub": str(db_user["id"]), "email": db_user["email"]})
    return {"token": token, "email": db_user["email"]}

@app.post("/api/auth/google")
def google_login(req: GoogleLoginRequest):
    # Verify token
    try:
        google_user = verify_google_token(req.token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}"
        )
        
    email = google_user.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token did not contain email"
        )
        
    db_user = db.get_user_by_email(email)
    if not db_user:
        # Create user with a secure random password hash
        random_password = str(uuid4())
        password_hash = get_password_hash(random_password)
        try:
            db.create_user(email, password_hash)
            db_user = db.get_user_by_email(email)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to register user from Google: {str(e)}"
            )
            
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User retrieval failed after registration"
        )
        
    token = create_access_token(data={"sub": str(db_user["id"]), "email": db_user["email"]})
    return {"token": token, "email": db_user["email"]}

# Chat Sessions Endpoints
@app.get("/api/chats")
def list_chats(current_user: dict = Depends(get_current_user)):
    return db.get_chat_sessions_for_user(current_user["id"])

@app.post("/api/chats")
def create_chat(current_user: dict = Depends(get_current_user)):
    session_id = str(uuid4())
    db.create_chat_session(session_id, current_user["id"], "New Chat")
    return {"session_id": session_id, "title": "New Chat"}

@app.get("/api/chats/{session_id}")
def get_chat_history(session_id: str, current_user: Optional[dict] = Depends(get_current_user_optional)):
    session = db.get_chat_session(session_id)
    if not session:
        return []
        
    if session["user_id"] is not None:
        if not current_user or session["user_id"] != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized access to chat session"
            )
    return db.get_history(session_id, limit=20)

@app.delete("/api/chats/{session_id}")
def delete_chat(session_id: str, current_user: Optional[dict] = Depends(get_current_user_optional)):
    session = db.get_chat_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
        
    user_id = current_user["id"] if current_user else None
    if session["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized to delete session"
        )
        
    db.delete_chat_session(session_id, user_id)
    return {"success": True}

# Chat Query Endpoint (Optional Authentication)
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: Optional[dict] = Depends(get_current_user_optional)):
    session_id = request.session_id
    user_id = current_user["id"] if current_user else None
    
    # If no session ID provided, create a new one automatically
    if not session_id:
        session_id = str(uuid4())
        db.create_chat_session(session_id, user_id, "New Chat")
    else:
        # Verify ownership of session ID
        session = db.get_chat_session(session_id)
        if not session:
            # Create session if it doesn't exist yet but has been provided
            db.create_chat_session(session_id, user_id, "New Chat")
            session = db.get_chat_session(session_id)
            
        if session["user_id"] is not None:
            if not current_user or session["user_id"] != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Unauthorized access to chat session"
                )
            
    # Get recent history from SQLite DB
    history = db.get_history(session_id, limit=6)
    
    # Save the user's incoming message
    db.save_message(session_id, "user", request.message)
    
    # If the session is currently named "New Chat", auto-generate a title from this first user message
    session = db.get_chat_session(session_id)
    if session and session["title"] == "New Chat":
        # Generate short title (e.g. up to 25 chars)
        clean_title = request.message.strip()
        if len(clean_title) > 28:
            clean_title = clean_title[:25] + "..."
        db.update_chat_session_title(session_id, clean_title)
    
    try:
        # Format history for RAG (convert sources array representation out or just pass list of dicts)
        # Note: the chat function expects history in format: [{"role": "user"|"assistant", "content": "..."}]
        formatted_history = []
        for h in history:
            formatted_history.append({"role": h["role"], "content": h["content"]})
            
        # Run RAG model chat
        result = chat(question=request.message, history=formatted_history)
        
        # Save assistant reply along with sources
        db.save_message(session_id, "assistant", result["answer"], result.get("sources", []))
        
        return {
            "answer": result["answer"],
            "sources": result.get("sources", []),
            "model_used": result.get("model_used", "unknown"),
            "session_id": session_id
        }
    except Exception as e:
        print(f"Error in chat_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@app.get("/debug_whatsapp")
def debug_whatsapp():
    import db.database as db
    from datetime import datetime
    conn = db.get_connection()
    cursor = conn.cursor()
    try:
        db_type = "PostgreSQL" if db.IS_POSTGRES else "SQLite"
        
        # Get recent WhatsApp sessions
        db.execute_query(cursor, """
            SELECT session_id, title, created_at FROM chat_sessions 
            WHERE session_id LIKE ? 
            ORDER BY created_at DESC LIMIT 5
        """, ('whatsapp_%',))
        sessions = [dict(r) for r in cursor.fetchall()]
        
        # Get recent WhatsApp messages
        db.execute_query(cursor, """
            SELECT id, session_id, role, content, timestamp FROM messages 
            WHERE session_id LIKE ? 
            ORDER BY timestamp DESC LIMIT 20
        """, ('whatsapp_%',))
        messages = []
        for r in cursor.fetchall():
            row_dict = dict(r)
            if "timestamp" in row_dict and isinstance(row_dict["timestamp"], datetime):
                row_dict["timestamp"] = row_dict["timestamp"].isoformat()
            messages.append(row_dict)
            
        return {
            "database_type": db_type,
            "has_database_url": os.getenv("DATABASE_URL") is not None,
            "sessions": sessions,
            "messages": messages
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()


# WhatsApp Webhook Endpoint (via Twilio)
@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    # Clean up phone number to make a nice session ID (e.g. whatsapp_+14155238886)
    clean_sender = From.replace("whatsapp:", "").strip()
    session_id = f"whatsapp_{clean_sender}"
    
    # 1. Verify/Create Chat Session in DB
    session = db.get_chat_session(session_id)
    if not session:
        # Create a persistent session for this phone number
        db.create_chat_session(session_id, user_id=None, title=f"WhatsApp {clean_sender}")
        
    # 2. Save user's message
    db.save_message(session_id, "user", Body)
    
    # 3. Get history for RAG
    history = db.get_history(session_id, limit=6)
    formatted_history = []
    for h in history:
        formatted_history.append({"role": h["role"], "content": h["content"]})
        
    try:
        # 4. Generate answer using RAG chatbot with WhatsApp conciseness flag
        result = chat(question=Body, history=formatted_history, is_whatsapp=True)
        answer = result["answer"]
        sources = result.get("sources", [])
        
        # 5. Save assistant reply along with sources
        db.save_message(session_id, "assistant", answer, sources)
        
        # Append short sources list to WhatsApp message if available (WhatsApp doesn't render HTML, so plain text URLs work best)
        if sources:
            sources_text = "\n\nSources:\n" + "\n".join([f"- {s}" for s in sources[:3]])
            answer_with_sources = answer + sources_text
        else:
            answer_with_sources = answer
            
        # Ensure we strictly stay under Twilio's 1600 character limit to prevent Error 63015
        if len(answer_with_sources) > 1575:
            answer = answer[:1450] + "...\n\n[Response truncated due to length limit. Please visit the website for full details.]"
            if sources:
                answer += "\n\nSources:\n" + "\n".join([f"- {s}" for s in sources[:3]])
        else:
            answer = answer_with_sources
    except Exception as e:
        print(f"Error in WhatsApp chat processing: {e}")
        answer = "⚠️ **Service Notice**: Sorry, I'm currently experiencing high demand. Please try again in a moment."
        
    # Escape special XML characters for TwiML compliance
    escaped_answer = answer.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    # 6. Return response in Twilio Markup Language (TwiML) format
    twiml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{escaped_answer}</Message>
</Response>"""
    
    return Response(content=twiml_response, media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)