export interface Document {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  file_type: string;
  document_type?: string;
  status: string;
  extracted_data?: any;
  metadata?: any;
  vector_id?: string;
  created_at: string;
  updated_at?: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  size: number;
}

export interface DocumentUploadResponse {
  document_id: number;
  filename: string;
  status: string;
  message: string;
}

export interface ChatMessage {
  id: number;
  content: string;
  role: string;
  timestamp: string;
}

export interface ChatSession {
  id: number;
  session_id: string;
  title: string;
  created_at: string;
  updated_at?: string;
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  sources: Source[];
  confidence: number;
}

export interface Source {
  filename: string;
  document_type: string;
  content: string;
  score: number;
}

export interface SearchRequest {
  query: string;
  document_types?: string[];
  limit: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  query: string;
}

export interface SearchResult {
  content: string;
  metadata: any;
  score: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}

export interface DocumentType {
  document_types: string[];
  file_extensions: string[];
}