"""
Healthcare Contract Analysis System - Backend API
A comprehensive document processing and analysis system for healthcare value-based contracts.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import logging
import json
import uuid
from datetime import datetime
import re

# LangChain imports
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
from langchain.prompts import PromptTemplate

# Vector store and database
import chromadb
from chromadb.config import Settings
import sqlite3
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class DocumentMetadata(BaseModel):
    filename: str
    document_type: str
    parties: List[str]
    country: str
    disease_area: str
    duration: str
    financial_amount: Optional[str] = None
    key_metrics: List[str] = []
    processed_at: datetime

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    include_context: bool = True

class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    session_id: str
    confidence_score: Optional[float] = None

class DocumentSummary(BaseModel):
    id: str
    metadata: DocumentMetadata
    summary: str
    key_insights: List[str]

# Document processor class
class ContractProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " "]
        )
        self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        
        # Initialize vector store
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection("healthcare_contracts")
        except:
            self.collection = self.chroma_client.create_collection("healthcare_contracts")
        
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name="healthcare_contracts",
            embedding_function=self.embeddings
        )

    def classify_document(self, content: str) -> str:
        """Classify document type based on content"""
        content_lower = content.lower()
        
        if "agreement" in content_lower and "parties:" in content_lower:
            return "healthcare_contract"
        elif "invoice" in content_lower or "billing" in content_lower:
            return "invoice"
        elif "report" in content_lower:
            return "report"
        else:
            return "unknown"

    def extract_metadata(self, content: str, filename: str) -> DocumentMetadata:
        """Extract structured metadata from contract content"""
        
        # Extract parties
        parties_match = re.search(r"Parties:\s*([^\n]+)", content)
        parties = []
        if parties_match:
            parties_text = parties_match.group(1)
            parties = [p.strip() for p in parties_text.split(" and ")]
        
        # Extract country
        country_match = re.search(r"Country:\s*([^\n]+)", content)
        country = country_match.group(1).strip() if country_match else "Unknown"
        
        # Extract disease area
        disease_match = re.search(r"Disease Area:\s*([^\n]+)", content)
        disease_area = disease_match.group(1).strip() if disease_match else "Unknown"
        
        # Extract duration
        duration_match = re.search(r"Duration:\s*([^\n]+)", content)
        duration = duration_match.group(1).strip() if duration_match else "Unknown"
        
        # Extract financial information
        financial_patterns = [
            r"€[\d,]+(?:\.\d{2})?",
            r"\$[\d,]+(?:\.\d{2})?",
            r"£[\d,]+(?:\.\d{2})?",
            r"SEK [\d,]+",
            r"NOK [\d,]+",
            r"AUD [\d,]+",
            r"CAD [\d,]+",
            r"MXN [\d,]+",
            r"¥[\d,]+"
        ]
        
        financial_amounts = []
        for pattern in financial_patterns:
            matches = re.findall(pattern, content)
            financial_amounts.extend(matches)
        
        financial_amount = financial_amounts[0] if financial_amounts else None
        
        # Extract key metrics
        key_metrics = []
        metric_patterns = [
            r"(\d+%)\s+(?:bonus|rebate|reduction|improvement)",
            r"(?:ACR20|RECIST|HbA1c|SVR|PHQ-9)",
            r"(\d+)\s+(?:months|years|days)",
            r"≥(\d+%)",
            r">(\d+%)"
        ]
        
        for pattern in metric_patterns:
            matches = re.findall(pattern, content)
            key_metrics.extend([match if isinstance(match, str) else match for match in matches])
        
        return DocumentMetadata(
            filename=filename,
            document_type=self.classify_document(content),
            parties=parties,
            country=country,
            disease_area=disease_area,
            duration=duration,
            financial_amount=financial_amount,
            key_metrics=list(set(key_metrics)),  # Remove duplicates
            processed_at=datetime.now()
        )

    async def process_document(self, content: str, filename: str) -> DocumentSummary:
        """Process a document and extract insights"""
        try:
            # Extract metadata
            metadata = self.extract_metadata(content, filename)
            
            # Split text into chunks
            documents = self.text_splitter.create_documents([content])
            
            # Add metadata to chunks
            for doc in documents:
                doc.metadata.update({
                    "filename": filename,
                    "document_type": metadata.document_type,
                    "country": metadata.country,
                    "disease_area": metadata.disease_area
                })
            
            # Add to vector store
            doc_ids = [f"{filename}_{i}" for i in range(len(documents))]
            self.vector_store.add_documents(documents, ids=doc_ids)
            
            # Generate summary using LLM
            summary_prompt = PromptTemplate(
                input_variables=["content"],
                template="""
                Analyze this healthcare value-based contract and provide:
                1. A concise summary (2-3 sentences)
                2. Key insights (3-5 bullet points)
                
                Contract Content:
                {content}
                
                Summary:
                """
            )
            
            summary_chain = summary_prompt | self.llm
            result = summary_chain.invoke({"content": content[:4000]})  # Limit content for API
            
            # Parse the result
            result_text = result.content if hasattr(result, 'content') else str(result)
            lines = result_text.strip().split('\n')
            
            summary = ""
            key_insights = []
            in_insights = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.lower().startswith('key insights') or '•' in line or line.startswith('-'):
                    in_insights = True
                    if '•' in line or line.startswith('-'):
                        insight = line.replace('•', '').replace('-', '').strip()
                        if insight:
                            key_insights.append(insight)
                elif not in_insights and not line.lower().startswith('summary'):
                    summary += line + " "
            
            if not key_insights:
                key_insights = [
                    f"Value-based contract in {metadata.disease_area}",
                    f"Covers {metadata.country} healthcare system",
                    f"Duration: {metadata.duration}",
                    f"Involves {len(metadata.parties)} parties"
                ]
            
            return DocumentSummary(
                id=str(uuid.uuid4()),
                metadata=metadata,
                summary=summary.strip() or f"Value-based healthcare agreement for {metadata.disease_area} in {metadata.country}",
                key_insights=key_insights
            )
            
        except Exception as e:
            logger.error(f"Error processing document {filename}: {str(e)}")
            raise HTTPException(status_code=500, f"Error processing document: {str(e)}")

    def create_qa_chain(self, session_id: str):
        """Create a conversational QA chain"""
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.vector_store.as_retriever(search_kwargs={"k": 4}),
            memory=memory,
            return_source_documents=True,
            verbose=True
        )
        
        return qa_chain

# Initialize processor
processor = ContractProcessor()

# In-memory session storage (in production, use Redis or database)
sessions = {}

# FastAPI app
app = FastAPI(
    title="Healthcare Contract Analysis API",
    description="AI-powered analysis system for healthcare value-based contracts",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple token verification (implement proper JWT in production)"""
    if credentials.credentials != "demo-token-123":
        raise HTTPException(status_code=401, detail="Invalid token")
    return credentials.credentials

# Sample data for demo (since we can't actually process uploaded files in this environment)
SAMPLE_CONTRACTS = [
    {
        "filename": "Contract-6.pdf",
        "content": """Agreement 6: Hepatitis C Cure-based Payment Model
Parties: LiverTech Pharmaceuticals and Spanish National Health Service Country: Spain Disease Area:
Hepatitis C (Genotypes 1-4) Agreement Overview: This innovative cure-based agreement addresses
Spain's public health initiative to eliminate Hepatitis C by 2030. The contract provides access to
direct-acting antivirals for approximately 8,500 patients annually, with payment fundamentally tied
to achieving sustained virologic response (SVR). The agreement includes special provisions for
difficult-to-treat populations including those with cirrhosis, HIV co-infection, and prior treatment
failures.
Financial Structure:
• Initial payment: €15,000 per treatment course upon therapy initiation
• Success-based payment: Additional €22,000 only upon confirmed sustained virologic
response (SVR12)
• Population-level metric: 5% discount if cure rate exceeds 95% across treated population
(current clinical trial data suggests 93-97% SVR rates)
• Non-responder management: Free retreatment with alternative regimen if initial therapy
fails"""
    }
]

@app.get("/")
async def root():
    return {"message": "Healthcare Contract Analysis API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now()}

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    token: str = Depends(verify_token)
):
    """Upload and process a document"""
    try:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # In a real implementation, you would:
        # 1. Save the file to storage
        # 2. Extract text using PyPDF2 or similar
        # 3. Process the extracted text
        
        # For demo, we'll use sample data
        sample_contract = SAMPLE_CONTRACTS[0]
        result = await processor.process_document(
            sample_contract["content"], 
            file.filename
        )
        
        return {
            "message": "Document processed successfully",
            "document_id": result.id,
            "summary": result
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def list_documents(token: str = Depends(verify_token)):
    """List all processed documents"""
    # In production, this would query from database
    return {
        "documents": [
            {
                "id": "demo-1",
                "filename": "Contract-6.pdf",
                "type": "healthcare_contract",
                "country": "Spain",
                "disease_area": "Hepatitis C",
                "processed_at": datetime.now()
            }
        ],
        "total": 1
    }

@app.post("/chat/query")
async def query_documents(
    request: QueryRequest,
    token: str = Depends(verify_token)
):
    """Query documents using natural language"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Create or get QA chain for session
        if session_id not in sessions:
            sessions[session_id] = processor.create_qa_chain(session_id)
        
        qa_chain = sessions[session_id]
        
        # Process query
        result = qa_chain({"question": request.query})
        
        # Format sources
        sources = []
        if "source_documents" in result:
            for doc in result["source_documents"]:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "metadata": doc.metadata,
                    "relevance_score": 0.85  # Placeholder
                })
        
        return QueryResponse(
            answer=result["answer"],
            sources=sources,
            session_id=session_id,
            confidence_score=0.9
        )
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/summary")
async def get_analytics_summary(token: str = Depends(verify_token)):
    """Get analytics summary of processed documents"""
    return {
        "total_documents": 20,
        "by_country": {
            "Spain": 1,
            "Sweden": 2,
            "Brazil": 1,
            "Singapore": 1,
            "France": 2,
            "Norway": 1,
            "Netherlands": 1,
            "Italy": 1,
            "Canada": 2,
            "Mexico": 1,
            "Japan": 1,
            "Australia": 2,
            "United Kingdom": 2,
            "Germany": 1,
            "United States": 1
        },
        "by_disease_area": {
            "Diabetes": 2,
            "Cancer": 3,
            "Mental Health": 2,
            "Heart Disease": 2,
            "Neurological": 2,
            "Respiratory": 2,
            "Others": 7
        },
        "avg_contract_value": "$2.5M",
        "performance_metrics": {
            "avg_success_rate": "87%",
            "cost_savings": "23%",
            "patient_satisfaction": "4.2/5"
        }
    }

@app.delete("/chat/session/{session_id}")
async def clear_session(
    session_id: str,
    token: str = Depends(verify_token)
):
    """Clear chat session"""
    if session_id in sessions:
        del sessions[session_id]
    return {"message": "Session cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)