from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class DocumentBase(BaseModel):
    filename: str
    document_type: Optional[str] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    document_type: Optional[str] = None
    status: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    document_metadata: Optional[Dict[str, Any]] = None


class DocumentResponse(DocumentBase):
    id: int
    original_filename: str
    file_size: int
    file_type: str
    status: str
    extracted_data: Optional[Dict[str, Any]] = None
    document_metadata: Optional[Dict[str, Any]] = None
    vector_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    size: int


class ChatMessageBase(BaseModel):
    content: str
    role: str


class ChatMessageCreate(ChatMessageBase):
    pass


class ChatMessageResponse(ChatMessageBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True


class ChatSessionBase(BaseModel):
    title: str


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    id: int
    session_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = []
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's question about the documents")
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sources: List[Dict[str, Any]] = []
    confidence: float


class DocumentUploadResponse(BaseModel):
    document_id: int
    filename: str
    status: str
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    document_types: Optional[List[str]] = None
    limit: int = 10


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str