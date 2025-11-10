"""
Unit tests for text2mem.services.models_service_openai module.

Focus areas:
1. Initialization and configuration of OpenAI models
2. API call handling
3. Error handling and retry logic
4. Response parsing and result processing
5. Batch operations
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from text2mem.services.models_service_openai import (
    OpenAIEmbeddingModel,
    OpenAIGenerationModel,
    OpenAIModelFactory,
    create_openai_models_service
)
from text2mem.services.models_service import EmbeddingResult, GenerationResult
from text2mem.core.config import ModelConfig


class TestOpenAIEmbeddingModel:
    """Tests for OpenAIEmbeddingModel."""
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_model_initialization(self, mock_openai_client):
        """Test initialization of the OpenAI embedding model."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        model_name = "text-embedding-3-small"
        api_key = "test-key"
        api_base = "https://api.openai.com/v1"
        organization = "test-org"
        model = OpenAIEmbeddingModel(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            organization=organization,
        )
        
        assert model.model_name == model_name
        assert model.api_key == api_key
        assert model.api_base == api_base
        assert model.organization == organization
        assert model.client == mock_client
        assert model.get_dimension() == 1536
        
        mock_openai_client.assert_called_once_with(
            api_key=api_key,
            base_url=api_base,
            organization=organization,
        )
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', False)
    def test_openai_embedding_model_no_openai_library(self):
        """Test behavior when OpenAI library is not installed."""
        with pytest.raises(ImportError) as exc_info:
            OpenAIEmbeddingModel()
        assert "openai package is required" in str(exc_info.value).lower()
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_model_no_api_key(self, mock_openai_client):
        """Test behavior when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OpenAIEmbeddingModel()
            assert "no openai api key provided" in str(exc_info.value).lower()
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_success(self, mock_openai_client):
        """Test successful embedding request."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_response.usage.total_tokens = 10
        mock_client.embeddings.create.return_value = mock_response
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        text = "Test text"
        result = model.embed_text(text)
        
        mock_client.embeddings.create.assert_called_once_with(
            model=model.model_name,
            input=text,
            encoding_format="float"
        )
        
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == [0.1, 0.2, 0.3, 0.4]
        assert result.text == text
        assert result.model == model.model_name
        assert result.tokens_used == 10
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_batch_success(self, mock_openai_client):
        """Test batch embedding requests."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4])
        ]
        mock_response.usage.total_tokens = 20
        mock_client.embeddings.create.return_value = mock_response
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        texts = ["Text1", "Text2"]
        results = model.embed_batch(texts)
        
        mock_client.embeddings.create.assert_called_once_with(
            model=model.model_name,
            input=texts,
            encoding_format="float"
        )
        
        assert len(results) == 2
        assert results[0].text == "Text1"
        assert results[0].embedding == [0.1, 0.2]
        assert results[1].text == "Text2"
        assert results[1].embedding == [0.3, 0.4]
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_api_error(self, mock_openai_client):
        """Test API error handling for embedding requests."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        mock_client.embeddings.create.side_effect = Exception("API call failed")
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        with pytest.raises(Exception) as exc_info:
            model.embed_text("Test text")
        assert "api call failed" in str(exc_info.value).lower()
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_different_models(self, mock_openai_client):
        """Test embedding dimension lookup for different models."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        models = [
            ("text-embedding-3-small", 1536),
            ("text-embedding-3-large", 3072),
            ("text-embedding-ada-002", 1536),
            ("unknown-model", 1536)
        ]
        
        for model_name, expected_dim in models:
            model = OpenAIEmbeddingModel(model_name=model_name, api_key="test-key")
            assert model.get_dimension() == expected_dim


class TestOpenAIGenerationModel:
    """Tests for OpenAIGenerationModel."""
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_model_initialization(self, mock_openai_client):
        """Test initialization of OpenAI generation model."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        model_name = "gpt-4"
        api_key = "test-key"
        api_base = "https://api.openai.com/v1"
        organization = "test-org"
        model = OpenAIGenerationModel(
            model_name=model_name,
            api_key=api_key,
            api_base=api_base,
            organization=organization,
        )
        
        assert model.model_name == model_name
        assert model.api_key == api_key
        assert model.api_base == api_base
        assert model.organization == organization
        assert model.client == mock_client
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_success(self, mock_openai_client):
        """Test successful text generation."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Generated reply"))]
        mock_response.usage = MagicMock(prompt_tokens=15, completion_tokens=25, total_tokens=40)
        mock_client.chat.completions.create.return_value = mock_response
        
        model = OpenAIGenerationModel(api_key="test-key")
        prompt = "Please answer the question"
        result = model.generate(prompt, temperature=0.8, max_tokens=256)
        
        mock_client.chat.completions.create.assert_called_once_with(
            model=model.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=256,
            top_p=1.0
        )
        
        assert isinstance(result, GenerationResult)
        assert result.text == "Generated reply"
        assert result.model == model.model_name
        assert result.prompt_tokens == 15
        assert result.completion_tokens == 25
        assert result.total_tokens == 40
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_structured(self, mock_openai_client):
        """Test structured output generation."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"result": "Structured data"}'))]
        mock_response.usage = MagicMock(prompt_tokens=20, completion_tokens=30, total_tokens=50)
        mock_client.chat.completions.create.return_value = mock_response
        
        model = OpenAIGenerationModel(api_key="test-key")
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        result = model.generate_structured("Generate JSON", schema)
        
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["response_format"] == {"type": "json_object"}
        
        assert result.text == '{"result": "Structured data"}'
        assert result.metadata["schema"] == schema
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_api_error(self, mock_openai_client):
        """Test error handling during generation API call."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API rate limit")
        
        model = OpenAIGenerationModel(api_key="test-key")
        with pytest.raises(Exception) as exc_info:
            model.generate("Test prompt")
        assert "api rate limit" in str(exc_info.value).lower()


class TestOpenAIModelFactory:
    """Tests for OpenAIModelFactory."""
    
    @patch('text2mem.services.models_service_openai.OpenAIEmbeddingModel')
    def test_create_embedding_model(self, mock_embedding_model):
        """Test creation of an embedding model from config."""
        config = MagicMock()
        config.embedding_provider = "openai"
        config.embedding_model = "text-embedding-3-small"
        config.openai_api_key = "test-key"
        config.openai_api_base = "https://api.openai.com/v1"
        config.openai_organization = "test-org"
        
        OpenAIModelFactory.create_embedding_model(config)
        
        mock_embedding_model.assert_called_once_with(
            model_name="text-embedding-3-small",
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            organization="test-org"
        )
    
    def test_create_embedding_model_wrong_provider(self):
        """Test embedding model creation with wrong provider."""
        config = MagicMock()
        config.embedding_provider = "ollama"
        
        with pytest.raises(ValueError) as exc_info:
            OpenAIModelFactory.create_embedding_model(config)
        assert "not an openai embedding model" in str(exc_info.value).lower()
    
    @patch('text2mem.services.models_service_openai.OpenAIGenerationModel')
    def test_create_generation_model(self, mock_generation_model):
        """Test creation of generation model from config."""
        config = MagicMock()
        config.generation_provider = "openai"
        config.generation_model = "gpt-4"
        config.openai_api_key = "test-key"
        config.openai_api_base = "https://api.openai.com/v1"
        config.openai_organization = "test-org"
        
        OpenAIModelFactory.create_generation_model(config)
        
        mock_generation_model.assert_called_once_with(
            model_name="gpt-4",
            api_key="test-key",
            api_base="https://api.openai.com/v1",
            organization="test-org"
        )


class TestOpenAIIntegration:
    """Integration tests for OpenAI model services."""
    
    @patch('text2mem.services.models_service_openai.OpenAIModelFactory')
    @patch('text2mem.services.models_service_openai.ModelsService')
    def test_create_openai_models_service(self, mock_models_service, mock_factory):
        """Test creation of OpenAI models service."""
        config = MagicMock()
        mock_embed_model = MagicMock()
        mock_gen_model = MagicMock()
        
        mock_factory.create_embedding_model.return_value = mock_embed_model
        mock_factory.create_generation_model.return_value = mock_gen_model
        
        result = create_openai_models_service(config)
        
        mock_factory.create_embedding_model.assert_called_once_with(config)
        mock_factory.create_generation_model.assert_called_once_with(config)
        
        mock_models_service.assert_called_once_with(
            embedding_model=mock_embed_model,
            generation_model=mock_gen_model
        )
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_models_environment_variables(self, mock_openai_client):
        """Test loading configuration from environment variables."""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'env-key',
            'OPENAI_API_BASE': 'https://custom.api.com/v1'
        }):
            embed_model = OpenAIEmbeddingModel()
            gen_model = OpenAIGenerationModel()
            
            assert embed_model.api_key == 'env-key'
            assert embed_model.api_base == 'https://custom.api.com/v1'
            assert gen_model.api_key == 'env-key'
            assert gen_model.api_base == 'https://custom.api.com/v1'
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_models_concurrent_usage(self, mock_openai_client):
        """Test concurrent usage of embedding and generation models."""
        import threading
        import time
        
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        def slow_embedding_response(*args, **kwargs):
            time.sleep(0.1)
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
            mock_response.usage.total_tokens = 5
            return mock_response
        
        def slow_generation_response(*args, **kwargs):
            time.sleep(0.1)
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="Reply"))]
            mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=10, total_tokens=15)
            return mock_response
        
        mock_client.embeddings.create.side_effect = slow_embedding_response
        mock_client.chat.completions.create.side_effect = slow_generation_response
        
        embed_model = OpenAIEmbeddingModel(api_key="test-key")
        gen_model = OpenAIGenerationModel(api_key="test-key")
        
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
