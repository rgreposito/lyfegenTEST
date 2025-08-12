import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.document import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionCreate
)
from app.services.chat_service import ChatService
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

# Initialize chat service
chat_service = ChatService()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(request: ChatSessionCreate):
    """Create a new chat session"""
    try:
        session_id = chat_service.create_session(request.title)
        session = chat_service.get_session(session_id)
        
        return ChatSessionResponse(
            id=1,  # Placeholder - in production this would come from database
            session_id=session_id,
            title=session["title"],
            created_at=session.get("created_at"),
            updated_at=session.get("updated_at"),
            messages=[]
        )
        
    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(session_id: str):
    """Get a specific chat session"""
    try:
        session = chat_service.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return ChatSessionResponse(
            id=1,  # Placeholder
            session_id=session_id,
            title=session["title"],
            created_at=session.get("created_at"),
            updated_at=session.get("updated_at"),
            messages=session.get("messages", [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """Send a message and get AI response"""
    try:
        # Generate response using chat service
        response_data = chat_service.generate_response(request.message, request.session_id or "")
        
        return ChatResponse(
            response=response_data["response"],
            session_id=response_data["session_id"],
            sources=response_data["sources"],
            confidence=response_data["confidence"]
        )
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions/{session_id}/summary")
async def get_conversation_summary(session_id: str):
    """Get a summary of the conversation"""
    try:
        summary = chat_service.get_conversation_summary(session_id)
        
        return {
            "session_id": session_id,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error getting conversation summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sessions/{session_id}/suggestions")
async def get_follow_up_suggestions(session_id: str, request: ChatRequest):
    """Get follow-up question suggestions"""
    try:
        suggestions = chat_service.suggest_follow_up_questions(request.message, session_id)
        
        return {
            "session_id": session_id,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"Error getting follow-up suggestions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str):
    """Delete a chat session"""
    try:
        # In production, this would delete from database
        # For now, we'll just remove from memory
        if session_id in chat_service.conversation_history:
            del chat_service.conversation_history[session_id]
        
        return {"message": "Chat session deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sessions")
async def list_chat_sessions():
    """List all chat sessions"""
    try:
        sessions = []
        for session_id, session_data in chat_service.conversation_history.items():
            sessions.append({
                "session_id": session_id,
                "title": session_data["title"],
                "message_count": len(session_data["messages"]),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at")
            })
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")