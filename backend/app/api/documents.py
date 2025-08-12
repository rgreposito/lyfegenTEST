import os
import shutil
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.document import Document as DocumentModel
from app.schemas.document import (
    DocumentResponse, 
    DocumentListResponse, 
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse
)
from app.services.document_processor import DocumentProcessor
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

# Initialize document processor
document_processor = DocumentProcessor()


def save_upload_file(upload_file: UploadFile) -> str:
    """Save uploaded file and return file path"""
    # Generate unique filename
    file_extension = os.path.splitext(upload_file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return file_path


async def process_document_background(file_path: str, document_id: int, db: Session):
    """Background task to process document"""
    try:
        # Get document from database
        document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        # Process document
        result = document_processor.process_document(file_path, document.original_filename)
        
        # Update document in database
        document.status = "completed"
        document.document_type = result["document_type"]
        document.extracted_data = result["extracted_data"]
        document.metadata = result["metadata"]
        document.vector_id = result["vector_id"]
        
        db.commit()
        logger.info(f"Document {document_id} processed successfully")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        # Update document status to failed
        document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        if document:
            document.status = "failed"
            db.commit()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process a document"""
    try:
        # Validate file type
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_extension} not allowed. Allowed types: {settings.allowed_extensions}"
            )
        
        # Validate file size
        if file.size > settings.max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File size {file.size} exceeds maximum allowed size {settings.max_file_size}"
            )
        
        # Save file
        file_path = save_upload_file(file)
        
        # Create document record in database
        document = DocumentModel(
            filename=os.path.basename(file_path),
            original_filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            file_type=file_extension,
            status="processing"
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # Start background processing
        background_tasks.add_task(process_document_background, file_path, document.id, db)
        
        return DocumentUploadResponse(
            document_id=document.id,
            filename=file.filename,
            status="processing",
            message="Document uploaded successfully and processing started"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 10,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all documents with optional filtering"""
    try:
        query = db.query(DocumentModel)
        
        if document_type:
            query = query.filter(DocumentModel.document_type == document_type)
        
        if status:
            query = query.filter(DocumentModel.status == status)
        
        total = query.count()
        documents = query.offset(skip).limit(limit).all()
        
        return DocumentListResponse(
            documents=documents,
            total=total,
            page=skip // limit + 1,
            size=limit
        )
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int, db: Session = Depends(get_db)):
    """Get a specific document by ID"""
    try:
        document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{document_id}")
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    """Delete a document"""
    try:
        document = db.query(DocumentModel).filter(DocumentModel.id == document_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete file from filesystem
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """Search documents using semantic search"""
    try:
        results = document_processor.search_documents(request.query, request.limit)
        
        # Filter by document type if specified
        if request.document_types:
            filtered_results = []
            for result in results:
                doc_type = result["metadata"].get("document_type", "")
                if doc_type in request.document_types:
                    filtered_results.append(result)
            results = filtered_results
        
        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/types")
async def get_document_types():
    """Get list of supported document types"""
    return {
        "document_types": [
            "contract",
            "invoice", 
            "report",
            "letter",
            "other"
        ],
        "file_extensions": settings.allowed_extensions
    }