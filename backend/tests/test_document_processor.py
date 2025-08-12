import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from app.services.document_processor import DocumentProcessor


class TestDocumentProcessor:
    @pytest.fixture
    def processor(self):
        with patch('app.services.document_processor.settings') as mock_settings:
            mock_settings.openai_api_key = 'test-key'
            mock_settings.chroma_persist_directory = './test_chroma'
            mock_settings.chunk_size = 1000
            mock_settings.chunk_overlap = 200
            return DocumentProcessor()

    def test_classify_document(self, processor):
        # Test contract classification
        contract_text = "This agreement is made between Party A and Party B..."
        result = processor.classify_document(contract_text)
        assert result in ['contract', 'invoice', 'report', 'letter', 'other']

    def test_extract_structured_data(self, processor):
        # Test invoice data extraction
        invoice_text = "Invoice #12345\nDate: 2024-01-01\nTotal: $100.00"
        result = processor.extract_structured_data(invoice_text, 'invoice')
        assert isinstance(result, dict)

    @patch('app.services.document_processor.PyPDFLoader')
    def test_load_document_pdf(self, mock_loader, processor):
        # Test PDF loading
        mock_docs = [Mock(page_content="Test content")]
        mock_loader.return_value.load.return_value = mock_docs
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'fake pdf content')
            file_path = f.name
        
        try:
            result = processor.load_document(file_path)
            assert len(result) == 1
            assert result[0].page_content == "Test content"
        finally:
            os.unlink(file_path)

    def test_search_documents(self, processor):
        # Test document search
        query = "test query"
        result = processor.search_documents(query, limit=5)
        assert isinstance(result, list)

    def test_invalid_file_type(self, processor):
        # Test unsupported file type
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            f.write(b'fake content')
            file_path = f.name
        
        try:
            with pytest.raises(ValueError):
                processor.load_document(file_path)
        finally:
            os.unlink(file_path)