# Document Processing and Analysis System

A production-ready AI application that processes and analyzes documents with intelligent classification, data extraction, and semantic search capabilities.

## Features

- **Document Processing Pipeline**: Handles PDF documents with intelligent classification
- **Multi-document Support**: Processes contracts, reports, invoices, and other document types
- **Structured Data Extraction**: Extracts key information from semi-structured documents
- **Semantic Search**: Advanced search capabilities with context-aware responses
- **Real-time Chat Interface**: Interactive chatbot for querying processed documents
- **Secure Document Storage**: Proper authentication and secure file handling

## Tech Stack

### Backend
- **FastAPI**: High-performance web framework
- **LangChain**: Document processing and AI pipeline
- **PostgreSQL**: Structured data storage
- **ChromaDB**: Vector database for semantic search
- **OpenAI API**: AI capabilities for text processing

### Frontend
- **React**: Modern web interface
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Responsive styling
- **Axios**: HTTP client for API communication

## Architecture

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Configuration and utilities
│   │   ├── models/         # Database models
│   │   ├── services/       # Business logic
│   │   └── utils/          # Helper functions
│   ├── requirements.txt    # Python dependencies
│   └── main.py            # Application entry point
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── utils/          # Utility functions
│   ├── package.json        # Node.js dependencies
│   └── tsconfig.json       # TypeScript configuration
├── docker-compose.yml      # Development environment
└── README.md              # This file
```

## Quick Start

1. **Clone the repository**
2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Add your OpenAI API key and other configurations
   ```
3. **Start the backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```
4. **Start the frontend**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation.

## Testing

- **Backend tests**: `pytest` in the backend directory
- **Frontend tests**: `npm test` in the frontend directory

## License

MIT License