import os
import uuid
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
        self.llm = ChatOpenAI(
            openai_api_key=settings.openai_api_key,
            temperature=0,
            model="gpt-3.5-turbo"
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
        )
        self.vector_store = None
        self._initialize_vector_store()
    
    def _initialize_vector_store(self):
        """Initialize the vector store"""
        try:
            self.vector_store = Chroma(
                persist_directory=settings.chroma_persist_directory,
                embedding_function=self.embeddings,
                collection_name="documents"
            )
            logger.info("Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
    
    def load_document(self, file_path: str) -> List[Document]:
        """Load document based on file type"""
        file_extension = Path(file_path).suffix.lower()
        
        try:
            if file_extension == ".pdf":
                loader = PyPDFLoader(file_path)
            elif file_extension == ".txt":
                loader = TextLoader(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            documents = loader.load()
            logger.info(f"Loaded {len(documents)} pages from {file_path}")
            return documents
        except Exception as e:
            logger.error(f"Error loading document {file_path}: {e}")
            raise
    
    def classify_document(self, text: str) -> str:
        """Classify document type using AI"""
        classification_prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            Analyze the following document text and classify it into one of these categories:
            - contract: Legal agreements, terms and conditions, contracts
            - invoice: Bills, invoices, financial documents
            - report: Reports, analysis, research documents
            - letter: Letters, correspondence, memos
            - other: Any other document type
            
            Document text:
            {text}
            
            Classification (respond with only the category name):
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=classification_prompt)
        result = chain.run(text=text[:2000])  # Limit text for classification
        return result.strip().lower()
    
    def extract_structured_data(self, text: str, document_type: str) -> Dict[str, Any]:
        """Extract structured data based on document type"""
        extraction_prompts = {
            "contract": """
            Extract key information from this contract document:
            - Parties involved
            - Contract value/amount
            - Start and end dates
            - Key terms and conditions
            - Signatures
            
            Document text:
            {text}
            
            Return as JSON format:
            """,
            "invoice": """
            Extract key information from this invoice:
            - Invoice number
            - Date
            - Due date
            - Total amount
            - Vendor/client information
            - Line items
            
            Document text:
            {text}
            
            Return as JSON format:
            """,
            "report": """
            Extract key information from this report:
            - Report title
            - Author
            - Date
            - Executive summary
            - Key findings
            - Recommendations
            
            Document text:
            {text}
            
            Return as JSON format:
            """
        }
        
        if document_type not in extraction_prompts:
            return {"raw_text": text[:1000]}
        
        prompt = PromptTemplate(
            input_variables=["text"],
            template=extraction_prompts[document_type]
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = chain.run(text=text[:3000])  # Limit text for extraction
        
        try:
            import json
            return json.loads(result)
        except:
            return {"extracted_text": result, "raw_text": text[:1000]}
    
    def process_document(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Main document processing pipeline"""
        try:
            # Load document
            documents = self.load_document(file_path)
            
            # Extract text
            full_text = "\n".join([doc.page_content for doc in documents])
            
            # Classify document
            document_type = self.classify_document(full_text)
            
            # Extract structured data
            extracted_data = self.extract_structured_data(full_text, document_type)
            
            # Split text into chunks
            text_chunks = self.text_splitter.split_documents(documents)
            
            # Generate unique ID for vector storage
            vector_id = str(uuid.uuid4())
            
            # Add metadata to chunks
            for chunk in text_chunks:
                chunk.metadata.update({
                    "document_id": vector_id,
                    "filename": original_filename,
                    "document_type": document_type,
                    "chunk_index": text_chunks.index(chunk)
                })
            
            # Store in vector database
            self.vector_store.add_documents(text_chunks)
            
            # Create metadata
            metadata = {
                "num_pages": len(documents),
                "num_chunks": len(text_chunks),
                "file_size": os.path.getsize(file_path),
                "processing_timestamp": str(uuid.uuid4())
            }
            
            return {
                "vector_id": vector_id,
                "document_type": document_type,
                "extracted_data": extracted_data,
                "metadata": metadata,
                "num_chunks": len(text_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}")
            raise
    
    def search_documents(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search documents using semantic search"""
        try:
            results = self.vector_store.similarity_search_with_score(query, k=limit)
            
            search_results = []
            for doc, score in results:
                search_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score)
                })
            
            return search_results
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise
    
    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a specific document"""
        try:
            # This would need to be implemented based on the specific vector store
            # For now, we'll return a placeholder
            return []
        except Exception as e:
            logger.error(f"Error getting document chunks: {e}")
            raise