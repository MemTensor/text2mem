"""
Unit tests for text2mem.services.models_service_ollama module.

Focus areas:
1. Initialization and configuration of Ollama models
2. Network request handling
3. Error handling and retry logic
4. Response parsing
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import threading
import time
from text2mem.services.models_service_ollama import OllamaEmbeddingModel, OllamaGenerationModel
from text2mem.services.models_service import EmbeddingResult, GenerationResult


class TestOllamaEmbeddingModel:
    """Tests for OllamaEmbeddingModel."""
    
    def test_ollama_embedding_model_initialization(self):
        """Test initialization of Ollama embedding model."""
        model = OllamaEmbeddingModel(
            model_name="nomic-embed-text",
            base_url="http://localhost:11434"
        )
        
        assert model.model_name == "nomic-embed-text"
        assert model.base_url == "http://localhost:11434"
        assert hasattr(model, 'client')
        assert model.get_dimension() == 768

    def test_ollama_embedding_default_dimension_unknown_model(self):
        """Unknown model name should return default dimension 768."""
        model = OllamaEmbeddingModel(model_name="some-unknown-embedder")
        assert model.get_dimension() == 768
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_success(self, mock_client_class):
        """Test successful embedding request."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3, 0.4]}
        mock_client.post.return_value = mock_response
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        text = "Test text"
        result = model.embed_text(text)
        
        mock_client.post.assert_called_once_with(
            f"{model.base_url}/api/embeddings",
            json={"model": model.model_name, "prompt": text},
        )
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == [0.1, 0.2, 0.3, 0.4]
        assert result.model == model.model_name
        assert result.text == text
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_http_error(self, mock_client_class):
        """Test handling of HTTP errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.post.side_effect = Exception("HTTP 500")
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception) as exc_info:
            model.embed_text("Test text")
        
        assert "HTTP 500" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_network_error(self, mock_client_class):
        """Test network connection error handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.post.side_effect = Exception("Connection failed")
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception) as exc_info:
            model.embed_text("Test text")
        
        assert "Connection failed" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_invalid_response(self, mock_client_class):
        """Test invalid JSON response handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_client.post.return_value = mock_response
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception):
            model.embed_text("Test text")


class TestOllamaGenerationModel:
    """Tests for OllamaGenerationModel."""
    
    def test_ollama_generation_model_initialization(self):
        """Test initialization of Ollama generation model."""
        model = OllamaGenerationModel(
            model_name="qwen2:0.5b",
            base_url="http://localhost:11434"
        )
        
        assert model.model_name == "qwen2:0.5b"
        assert model.base_url == "http://localhost:11434"
        assert hasattr(model, 'client')
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_success(self, mock_client_class):
        """Test successful text generation request."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "This is the generated response text",
            "done": True
        }
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        prompt = "Please answer the question"
        result = model.generate(prompt)
        
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{model.base_url}/api/generate"
        
        request_data = call_args[1]['json']
        assert request_data['model'] == model.model_name
        assert request_data['prompt'] == prompt
        assert request_data['stream'] is False
        
        assert isinstance(result, GenerationResult)
        assert result.text == "This is the generated response text"
        assert result.model == model.model_name
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_with_options(self, mock_client_class):
        """Test generation request with additional options."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Response", "done": True}
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        model.generate("Test prompt", temperature=0.8, max_tokens=256)
        
        call_args = mock_client.post.call_args
        request_data = call_args[1]['json']
        
        assert 'options' in request_data
        options = request_data['options']
        assert options['temperature'] == 0.8
        assert options['num_predict'] == 256
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_incomplete_response(self, mock_client_class):
        """Test handling of incomplete response (done=False)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.json.return_value = {"response": "Partial reply", "done": False}
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        result = model.generate("Test prompt")
        
        assert result.text == "Partial reply"
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_missing_response_field(self, mock_client_class):
        """Test response missing the 'response' field."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.json.return_value = {"done": True}
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        
        with pytest.raises(Exception):
            model.generate("Test prompt")


class TestOllamaIntegration:
    """Integration tests for Ollama service behavior."""
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_models_with_same_base_url(self, mock_client_class):
        """Test embedding and generation models using the same base_url."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        def side_effect(*args, **kwargs):
            mock_response = Mock()
            if "embeddings" in args[0]:
                mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
            else:
                mock_response.json.return_value = {"response": "Generated text", "done": True}
            return mock_response
        
        mock_client.post.side_effect = side_effect
        
        base_url = "http://localhost:11434"
        embed_model = OllamaEmbeddingModel("nomic-embed-text", base_url=base_url)
        gen_model = OllamaGenerationModel("qwen2:0.5b", base_url=base_url)
        
        embed_result = embed_model.embed_text("Test")
        gen_result = gen_model.generate("Test")
        
        assert embed_result.embedding == [0.1, 0.2, 0.3]
        assert gen_result.text == "Generated text"
        
        assert mock_client.post.call_count == 2
        calls = [call[0][0] for call in mock_client.post.call_args_list]
        assert f"{base_url}/api/embeddings" in calls
        assert f"{base_url}/api/generate" in calls
    
    def test_ollama_models_different_timeouts(self):
        """Test models with different timeout configurations."""
        embed_model = OllamaEmbeddingModel("nomic-embed-text")
        gen_model = OllamaGenerationModel("qwen2:0.5b")
        
        assert embed_model.model_name == "nomic-embed-text"
        assert gen_model.model_name == "qwen2:0.5b"

    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_clients_timeouts(self, mock_client_class):
        """Verify that httpx.Client is created with different timeouts (60s for embedding, 120s for generation)."""
        embed_client = MagicMock()
        gen_client = MagicMock()
        mock_client_class.side_effect = [embed_client, gen_client]

        OllamaEmbeddingModel("nomic-embed-text")
        OllamaGenerationModel("qwen2:0.5b")

        calls = mock_client_class.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs.get('timeout') == 60.0
        assert calls[1].kwargs.get('timeout') == 120.0
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_models_concurrent_requests(self, mock_client_class):
        """Test concurrent request handling."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        def slow_response(*args, **kwargs):
            time.sleep(0.1)
            mock_response = Mock()
            if "embeddings" in args[0]:
                mock_response.json.return_value = {"embedding": [0.1, 0.2]}
            else:
                mock_response.json.return_value = {"response": "Reply", "done": True}
            return mock_response
        
        mock_client.post.side_effect = slow_response
        
        embed_model = OllamaEmbeddingModel("nomic-embed-text")
        gen_model = OllamaGenerationModel("qwen2:0.5b")
        
        results = []
        
        def embed_task():
            result = embed_model.embed_text("Test")
            results.append(("embed", result))
        
        def gen_task():
            result = gen_model.generate("Test")
            results.append(("gen", result))
        
        threads = [
            threading.Thread(target=embed_task),
            threading.Thread(target=gen_task)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 2
        result_types = [r[0] for r in results]
        assert "embed" in result_types
        assert "gen" in result_types
