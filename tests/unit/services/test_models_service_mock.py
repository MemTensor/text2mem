"""
Unit tests for text2mem.services.models_service_mock module.

Focus areas:
1. Service provider factory
2. Multi-provider support
3. Configuration validation and error handling
4. Service mode switching mechanism
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from text2mem.services.models_service_mock import (
    create_models_service,
    create_openai_models_service,
    create_ollama_models_service,
    create_mock_models_service
)
from text2mem.core.config import ModelConfig


class TestModelsServiceProviders:
    """Tests for model service providers."""
    
    def test_create_mock_models_service(self):
        """Test creation of mock model service."""
        service = create_mock_models_service()
        
        assert service is not None
        assert hasattr(service, 'embedding_model')
        assert hasattr(service, 'generation_model')
    
    @patch('text2mem.services.models_service_mock.create_openai_models_service')
    def test_create_models_service_openai_mode(self, mock_create_openai):
        """Test creating model service in OpenAI mode."""
        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service
        
        result = create_models_service(mode="openai")
        
        assert result == mock_service
    
    @patch('text2mem.services.models_service_mock.create_ollama_models_service')  
    def test_create_models_service_ollama_mode(self, mock_create_ollama):
        """Test creating model service in Ollama mode."""
        mock_service = MagicMock()
        mock_create_ollama.return_value = mock_service
        
        result = create_models_service(mode="ollama")
        
        assert result == mock_service
    
    def test_create_models_service_mock_mode(self):
        """Test creating model service in mock mode."""
        result = create_models_service(mode="mock")
        
        assert result is not None
        assert hasattr(result, 'embedding_model')
        assert hasattr(result, 'generation_model')
    
    def test_create_models_service_invalid_mode(self):
        """Test invalid service mode."""
        with pytest.raises(ValueError) as exc_info:
            create_models_service(mode="invalid")
        
        assert "Unknown model service mode" in str(exc_info.value)
    
    @patch.dict('os.environ', {'MODEL_SERVICE': 'openai'})
    @patch('text2mem.services.models_service_mock.create_openai_models_service')
    def test_create_models_service_auto_mode_with_env(self, mock_create_openai):
        """Test 'auto' mode using environment variable."""
        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service
        
        result = create_models_service(mode="auto")
        
        assert result == mock_service


class TestModelConfigValidation:
    """Tests for model configuration validation."""
    
    def test_valid_config_attributes(self):
        """Test valid configuration attributes."""
        config = MagicMock()
        config.embedding_provider = "openai"
        config.generation_provider = "openai"
        config.embedding_model = "text-embedding-3-small"
        config.generation_model = "gpt-3.5-turbo"
        
        # Validate required attributes exist
        assert hasattr(config, 'embedding_provider')
        assert hasattr(config, 'generation_provider')
        assert hasattr(config, 'embedding_model')
        assert hasattr(config, 'generation_model')


class TestProviderFactoryIntegration:
    """Integration tests for provider factory creation."""

    @patch('text2mem.services.models_service_openai.create_openai_models_service')
    @patch('text2mem.services.models_service_mock.ModelConfig')
    def test_openai_service_creation(self, mock_model_config, mock_create_openai):
        """Test OpenAI service creation."""
        mock_config = MagicMock()
        mock_model_config.load_openai_config.return_value = mock_config

        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service

        result = create_openai_models_service()

        mock_model_config.load_openai_config.assert_called_once()
        mock_create_openai.assert_called_once_with(mock_config)
        assert result == mock_service

    @patch('text2mem.services.models_service_ollama.create_models_service_from_config')
    @patch('text2mem.services.models_service_mock.ModelConfig')
    def test_ollama_service_creation(self, mock_model_config, mock_create_from_config):
        """Test Ollama service creation."""
        mock_config = MagicMock()
        mock_model_config.load_ollama_config.return_value = mock_config

        mock_service = MagicMock()
        mock_create_from_config.return_value = mock_service

        result = create_ollama_models_service()

        mock_model_config.load_ollama_config.assert_called_once()
        mock_create_from_config.assert_called_once_with(mock_config)
        assert result == mock_service


class TestProviderErrorHandling:
    """Tests for provider error handling."""
    
    @patch('text2mem.services.models_service_openai.create_openai_models_service')
    @patch('text2mem.services.models_service_mock.ModelConfig')
    def test_openai_service_creation_error(self, mock_model_config, mock_create_openai):
        """Test error during OpenAI service creation."""
        mock_config = MagicMock()
        mock_model_config.load_openai_config.return_value = mock_config
        
        # Simulate creation failure
        mock_create_openai.side_effect = Exception("Invalid API key")
        
        with pytest.raises(Exception) as exc_info:
            create_openai_models_service()
        
        assert "Invalid API key" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.create_models_service_from_config')
    @patch('text2mem.services.models_service_mock.ModelConfig')
    def test_ollama_service_creation_error(self, mock_model_config, mock_create_from_config):
        """Test error during Ollama service creation."""
        mock_config = MagicMock()
        mock_model_config.load_ollama_config.return_value = mock_config
        
        # Simulate creation failure
        mock_create_from_config.side_effect = Exception("Ollama service not running")
        
        with pytest.raises(Exception) as exc_info:
            create_ollama_models_service()
        
        assert "Ollama service not running" in str(exc_info.value)


class TestProviderPerformance:
    """Performance-related tests for provider factory."""
    
    def test_multiple_mock_service_creations(self):
        """Test creating multiple mock services quickly."""
        import time
        
        start_time = time.time()
        results = [create_mock_models_service() for _ in range(5)]
        end_time = time.time()
        
        # Validate all services were created
        assert len(results) == 5
        
        # Validate creation time (should be fast)
        assert end_time - start_time < 1.0
        
        # Validate each service has required components
        for service in results:
            assert hasattr(service, 'embedding_model')
            assert hasattr(service, 'generation_model')
    
    @patch('text2mem.services.models_service_mock.create_openai_models_service')
    @patch('text2mem.services.models_service_mock.create_ollama_models_service')
    def test_service_mode_switching(self, mock_create_ollama, mock_create_openai):
        """Test switching between service modes."""
        openai_service = MagicMock()
        ollama_service = MagicMock()
        mock_create_openai.return_value = openai_service
        mock_create_ollama.return_value = ollama_service
        
        modes = ["openai", "ollama", "mock"]
        results = [(mode, create_models_service(mode=mode)) for mode in modes]
        
        assert len(results) == 3
        
        # Verify OpenAI and Ollama services were each called once
        assert mock_create_openai.call_count == 1
        assert mock_create_ollama.call_count == 1
        
        # Validate results by mode
        mode_results = {mode: result for mode, result in results}
        assert mode_results["openai"] == openai_service
        assert mode_results["ollama"] == ollama_service
        assert mode_results["mock"] is not None
