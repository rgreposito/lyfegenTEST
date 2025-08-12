import axios, { AxiosResponse } from 'axios';
import {
  Document,
  DocumentListResponse,
  DocumentUploadResponse,
  ChatSession,
  ChatRequest,
  ChatResponse,
  SearchRequest,
  SearchResponse,
  DocumentType,
  ApiError
} from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add any auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    const apiError: ApiError = {
      detail: error.response?.data?.detail || 'An error occurred',
      status_code: error.response?.status,
    };
    return Promise.reject(apiError);
  }
);

// Document API
export const documentApi = {
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (params?: {
    skip?: number;
    limit?: number;
    document_type?: string;
    status?: string;
  }): Promise<DocumentListResponse> => {
    const response = await api.get('/documents/', { params });
    return response.data;
  },

  get: async (id: number): Promise<Document> => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },

  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post('/documents/search', request);
    return response.data;
  },

  getTypes: async (): Promise<DocumentType> => {
    const response = await api.get('/documents/types');
    return response.data;
  },
};

// Chat API
export const chatApi = {
  createSession: async (title: string): Promise<ChatSession> => {
    const response = await api.post('/chat/sessions', { title });
    return response.data;
  },

  getSession: async (sessionId: string): Promise<ChatSession> => {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  },

  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await api.post('/chat/message', request);
    return response.data;
  },

  getSummary: async (sessionId: string): Promise<{ summary: string }> => {
    const response = await api.get(`/chat/sessions/${sessionId}/summary`);
    return response.data;
  },

  getSuggestions: async (sessionId: string, message: string): Promise<{ suggestions: string[] }> => {
    const response = await api.post(`/chat/sessions/${sessionId}/suggestions`, { message });
    return response.data;
  },

  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/chat/sessions/${sessionId}`);
  },

  listSessions: async (): Promise<{ sessions: any[]; total: number }> => {
    const response = await api.get('/chat/sessions');
    return response.data;
  },
};

// Health check
export const healthApi = {
  check: async (): Promise<{ status: string; app_name: string; version: string }> => {
    const response = await axios.get(`${API_BASE_URL.replace('/api/v1', '')}/health`);
    return response.data;
  },
};

export default api;