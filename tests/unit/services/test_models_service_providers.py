"""
测试 text2mem.services.models_service_providers 模块
重点测试：
1. 服务提供商工厂
2. 多提供商支持
3. 配置验证和错误处理
4. 服务切换机制
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from text2mem.services.models_service_providers import (
    create_models_service,
    create_openai_models_service,
    create_ollama_models_service,
    create_mock_models_service
)
from text2mem.core.config import ModelConfig


class TestModelsServiceProviders:
    """测试模型服务提供商"""
    
    def test_create_mock_models_service(self):
        """测试创建Mock模型服务"""
        service = create_mock_models_service()
        
        assert service is not None
        assert hasattr(service, 'embedding_model')
        assert hasattr(service, 'generation_model')
    
    @patch('text2mem.services.models_service_providers.create_openai_models_service')
    def test_create_models_service_openai_mode(self, mock_create_openai):
        """测试创建OpenAI模式的模型服务"""
        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service
        
        result = create_models_service(mode="openai")
        
        assert result == mock_service
    
    @patch('text2mem.services.models_service_providers.create_ollama_models_service')  
    def test_create_models_service_ollama_mode(self, mock_create_ollama):
        """测试创建Ollama模式的模型服务"""
        mock_service = MagicMock()
        mock_create_ollama.return_value = mock_service
        
        result = create_models_service(mode="ollama")
        
        assert result == mock_service
    
    def test_create_models_service_mock_mode(self):
        """测试创建Mock模式的模型服务"""
        result = create_models_service(mode="mock")
        
        assert result is not None
        assert hasattr(result, 'embedding_model')
        assert hasattr(result, 'generation_model')
    
    def test_create_models_service_invalid_mode(self):
        """测试无效模式"""
        with pytest.raises(ValueError) as exc_info:
            create_models_service(mode="invalid")
        
        assert "未知的模型服务模式" in str(exc_info.value)
    
    @patch.dict('os.environ', {'MODEL_SERVICE': 'openai'})
    @patch('text2mem.services.models_service_providers.create_openai_models_service')
    def test_create_models_service_auto_mode_with_env(self, mock_create_openai):
        """测试自动模式使用环境变量"""
        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service
        
        result = create_models_service(mode="auto")
        
        assert result == mock_service


class TestModelConfigValidation:
    """测试模型配置验证"""
    
    def test_valid_config_attributes(self):
        """测试有效配置的属性"""
        config = MagicMock()
        config.embedding_provider = "openai"
        config.generation_provider = "openai"
        config.embedding_model = "text-embedding-3-small"
        config.generation_model = "gpt-3.5-turbo"
        
        # 验证配置属性存在
        assert hasattr(config, 'embedding_provider')
        assert hasattr(config, 'generation_provider')
        assert hasattr(config, 'embedding_model')
        assert hasattr(config, 'generation_model')


class TestProviderFactoryIntegration:
    """测试提供商工厂集成"""

    @patch('text2mem.services.models_service_openai.create_openai_models_service')
    @patch('text2mem.services.models_service_providers.ModelConfig')
    def test_openai_service_creation(self, mock_model_config, mock_create_openai):
        """测试OpenAI服务创建"""
        mock_config = MagicMock()
        mock_model_config.load_openai_config.return_value = mock_config

        mock_service = MagicMock()
        mock_create_openai.return_value = mock_service

        result = create_openai_models_service()

        mock_model_config.load_openai_config.assert_called_once()
        mock_create_openai.assert_called_once_with(mock_config)
        assert result == mock_service

    @patch('text2mem.services.models_service_ollama.create_models_service_from_config')
    @patch('text2mem.services.models_service_providers.ModelConfig')
    def test_ollama_service_creation(self, mock_model_config, mock_create_from_config):
        """测试Ollama服务创建"""
        mock_config = MagicMock()
        mock_model_config.load_ollama_config.return_value = mock_config

        mock_service = MagicMock()
        mock_create_from_config.return_value = mock_service

        result = create_ollama_models_service()

        mock_model_config.load_ollama_config.assert_called_once()
        mock_create_from_config.assert_called_once_with(mock_config)
        assert result == mock_service


class TestProviderErrorHandling:
    """测试提供商错误处理"""
    
    @patch('text2mem.services.models_service_openai.create_openai_models_service')
    @patch('text2mem.services.models_service_providers.ModelConfig')
    def test_openai_service_creation_error(self, mock_model_config, mock_create_openai):
        """测试OpenAI服务创建错误"""
        mock_config = MagicMock()
        mock_model_config.load_openai_config.return_value = mock_config
        
        # 模拟服务创建失败
        mock_create_openai.side_effect = Exception("API密钥无效")
        
        with pytest.raises(Exception) as exc_info:
            create_openai_models_service()
        
        assert "API密钥无效" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.create_models_service_from_config')
    @patch('text2mem.services.models_service_providers.ModelConfig')
    def test_ollama_service_creation_error(self, mock_model_config, mock_create_from_config):
        """测试Ollama服务创建错误"""
        mock_config = MagicMock()
        mock_model_config.load_ollama_config.return_value = mock_config
        
        # 模拟服务创建失败
        mock_create_from_config.side_effect = Exception("Ollama服务未运行")
        
        with pytest.raises(Exception) as exc_info:
            create_ollama_models_service()
        
        assert "Ollama服务未运行" in str(exc_info.value)


class TestProviderPerformance:
    """测试提供商性能相关"""
    
    def test_multiple_mock_service_creations(self):
        """测试多次Mock服务创建"""
        import time
        
        # 测试多次快速创建
        start_time = time.time()
        
        results = []
        for i in range(5):
            result = create_mock_models_service()
            results.append(result)
        
        end_time = time.time()
        
        # 验证所有服务都创建成功
        assert len(results) == 5
        
        # 验证创建时间合理（应该很快）
        assert end_time - start_time < 1.0
        
        # 验证每个服务都有必要的组件
        for service in results:
            assert hasattr(service, 'embedding_model')
            assert hasattr(service, 'generation_model')
    
    @patch('text2mem.services.models_service_providers.create_openai_models_service')
    @patch('text2mem.services.models_service_providers.create_ollama_models_service')
    def test_service_mode_switching(self, mock_create_ollama, mock_create_openai):
        """测试服务模式切换"""
        openai_service = MagicMock()
        ollama_service = MagicMock()
        mock_create_openai.return_value = openai_service
        mock_create_ollama.return_value = ollama_service
        
        # 测试不同模式
        modes = ["openai", "ollama", "mock"]
        results = []
        
        for mode in modes:
            result = create_models_service(mode=mode)
            results.append((mode, result))
        
        # 验证结果
        assert len(results) == 3
        
        # 验证OpenAI和Ollama调用
        assert mock_create_openai.call_count == 1
        assert mock_create_ollama.call_count == 1
        
        # 验证结果类型
        mode_results = {mode: result for mode, result in results}
        assert mode_results["openai"] == openai_service
        assert mode_results["ollama"] == ollama_service
        assert mode_results["mock"] is not None
