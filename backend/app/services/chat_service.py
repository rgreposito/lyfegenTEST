import uuid
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.core.config import settings
from app.services.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            temperature=0.7,
            model="gpt-3.5-turbo"
        )
        self.document_processor = DocumentProcessor()
        self.conversation_history = {}  # In production, this should be in a database
    
    def create_session(self, title: str = "New Chat") -> str:
        """Create a new chat session"""
        session_id = str(uuid.uuid4())
        self.conversation_history[session_id] = {
            "title": title,
            "messages": [],
            "context": []
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get chat session by ID"""
        return self.conversation_history.get(session_id)
    
    def add_message(self, session_id: str, content: str, role: str = "user"):
        """Add a message to the conversation history"""
        if session_id not in self.conversation_history:
            raise ValueError(f"Session {session_id} not found")
        
        message = {
            "content": content,
            "role": role,
            "timestamp": str(uuid.uuid4())  # In production, use actual timestamp
        }
        
        self.conversation_history[session_id]["messages"].append(message)
    
    def search_relevant_context(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant document context"""
        try:
            search_results = self.document_processor.search_documents(query, limit=limit)
            return search_results
        except Exception as e:
            logger.error(f"Error searching for context: {e}")
            return []
    
    def generate_response(self, query: str, session_id: str) -> Dict[str, Any]:
        """Generate a context-aware response"""
        try:
            # Search for relevant document context
            relevant_context = self.search_relevant_context(query)
            
            # Get conversation history
            session = self.get_session(session_id)
            if not session:
                session_id = self.create_session()
                session = self.get_session(session_id)
            
            # Build context from relevant documents
            context_text = ""
            sources = []
            
            if relevant_context:
                context_text = "\n\n".join([
                    f"Document: {result['metadata'].get('filename', 'Unknown')}\n"
                    f"Content: {result['content']}"
                    for result in relevant_context
                ])
                
                sources = [
                    {
                        "filename": result["metadata"].get("filename", "Unknown"),
                        "document_type": result["metadata"].get("document_type", "Unknown"),
                        "content": result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"],
                        "score": result["score"]
                    }
                    for result in relevant_context
                ]
            
            # Build conversation history
            history_text = ""
            if session["messages"]:
                history_text = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in session["messages"][-5:]  # Last 5 messages for context
                ])
            
            # Create response prompt
            response_prompt = PromptTemplate(
                input_variables=["query", "context", "history"],
                template="""
                You are a helpful AI assistant that answers questions about documents. 
                Use the provided context from documents to answer questions accurately.
                
                Context from documents:
                {context}
                
                Conversation history:
                {history}
                
                Current question: {query}
                
                Instructions:
                1. Answer based on the document context provided
                2. If the information is not in the documents, say so clearly
                3. Be concise but informative
                4. If you reference specific documents, mention the filename
                5. Maintain conversation flow and context
                
                Response:
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=response_prompt)
            response = chain.run(
                query=query,
                context=context_text if context_text else "No relevant documents found.",
                history=history_text if history_text else "No previous conversation."
            )
            
            # Add user message to history
            self.add_message(session_id, query, "user")
            
            # Add assistant response to history
            self.add_message(session_id, response, "assistant")
            
            # Calculate confidence based on context relevance
            confidence = 0.8 if relevant_context else 0.3
            
            return {
                "response": response.strip(),
                "session_id": session_id,
                "sources": sources,
                "confidence": confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "session_id": session_id,
                "sources": [],
                "confidence": 0.0
            }
    
    def get_conversation_summary(self, session_id: str) -> str:
        """Generate a summary of the conversation"""
        try:
            session = self.get_session(session_id)
            if not session or not session["messages"]:
                return "No conversation to summarize."
            
            # Get all messages
            messages_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in session["messages"]
            ])
            
            summary_prompt = PromptTemplate(
                input_variables=["messages"],
                template="""
                Summarize the following conversation in 2-3 sentences:
                
                {messages}
                
                Summary:
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=summary_prompt)
            summary = chain.run(messages=messages_text)
            
            return summary.strip()
            
        except Exception as e:
            logger.error(f"Error generating conversation summary: {e}")
            return "Unable to generate summary."
    
    def suggest_follow_up_questions(self, query: str, session_id: str) -> List[str]:
        """Generate follow-up question suggestions"""
        try:
            session = self.get_session(session_id)
            if not session:
                return []
            
            # Get recent context
            recent_messages = session["messages"][-3:] if session["messages"] else []
            recent_text = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in recent_messages
            ])
            
            suggestion_prompt = PromptTemplate(
                input_variables=["query", "recent_context"],
                template="""
                Based on the current question and recent conversation context, suggest 3 relevant follow-up questions.
                Make them specific and helpful for understanding the documents better.
                
                Current question: {query}
                Recent context: {recent_context}
                
                Suggest 3 follow-up questions:
                1.
                2.
                3.
                """
            )
            
            chain = LLMChain(llm=self.llm, prompt=suggestion_prompt)
            suggestions = chain.run(
                query=query,
                recent_context=recent_text if recent_text else "No recent context."
            )
            
            # Parse suggestions
            lines = suggestions.strip().split('\n')
            follow_up_questions = []
            
            for line in lines:
                line = line.strip()
                if line and (line.startswith(('1.', '2.', '3.')) or line[0].isdigit()):
                    question = line.split('.', 1)[1].strip() if '.' in line else line
                    if question:
                        follow_up_questions.append(question)
            
            return follow_up_questions[:3]  # Return max 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating follow-up suggestions: {e}")
            return []