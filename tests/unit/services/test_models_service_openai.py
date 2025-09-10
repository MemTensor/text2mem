"""
测试 text2mem.services.models_service_openai 模块
重点测试：
1. OpenAI模型的初始化和配置
2. API调用处理
3. 错误处理和重试机制
4. 响应解析和结果处理
5. 批量处理
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
    """测试OpenAIEmbeddingModel"""
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_model_initialization(self, mock_openai_client):
        """测试OpenAI嵌入模型初始化"""
        # 模拟OpenAI客户端
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
        
        # 验证客户端初始化参数
        mock_openai_client.assert_called_once_with(
            api_key=api_key,
            base_url=api_base,
            organization=organization,
        )
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', False)
    def test_openai_embedding_model_no_openai_library(self):
        """测试没有安装OpenAI库的情况"""
        with pytest.raises(ImportError) as exc_info:
            OpenAIEmbeddingModel()
        
        assert "需要安装 openai" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_model_no_api_key(self, mock_openai_client):
        """测试没有API密钥的情况"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                OpenAIEmbeddingModel()
            
            assert "未提供 OpenAI API 密钥" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_success(self, mock_openai_client):
        """测试成功的嵌入请求"""
        # 模拟OpenAI响应
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4])]
        mock_response.usage.total_tokens = 10
        mock_client.embeddings.create.return_value = mock_response
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        text = "测试文本"
        result = model.embed_text(text)
        
        # 验证API调用
        mock_client.embeddings.create.assert_called_once_with(
            model=model.model_name,
            input=text,
            encoding_format="float"
        )
        
        # 验证结果
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == [0.1, 0.2, 0.3, 0.4]
        assert result.text == text
        assert result.model == model.model_name
        assert result.tokens_used == 10
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_batch_success(self, mock_openai_client):
        """测试批量嵌入请求"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # 模拟批量响应
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4])
        ]
        mock_response.usage.total_tokens = 20
        mock_client.embeddings.create.return_value = mock_response
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        texts = ["文本1", "文本2"]
        results = model.embed_batch(texts)
        
        # 验证API调用
        mock_client.embeddings.create.assert_called_once_with(
            model=model.model_name,
            input=texts,
            encoding_format="float"
        )
        
        # 验证结果
        assert len(results) == 2
        assert results[0].text == "文本1"
        assert results[0].embedding == [0.1, 0.2]
        assert results[1].text == "文本2"
        assert results[1].embedding == [0.3, 0.4]
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_api_error(self, mock_openai_client):
        """测试API错误处理"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # 模拟API错误
        mock_client.embeddings.create.side_effect = Exception("API调用失败")
        
        model = OpenAIEmbeddingModel(api_key="test-key")
        
        with pytest.raises(Exception) as exc_info:
            model.embed_text("测试文本")
        
        assert "API调用失败" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_embedding_different_models(self, mock_openai_client):
        """测试不同模型的维度"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # 测试不同模型
        models = [
            ("text-embedding-3-small", 1536),
            ("text-embedding-3-large", 3072),
            ("text-embedding-ada-002", 1536),
            ("unknown-model", 1536)  # 默认维度
        ]
        
        for model_name, expected_dim in models:
            model = OpenAIEmbeddingModel(model_name=model_name, api_key="test-key")
            assert model.get_dimension() == expected_dim


class TestOpenAIGenerationModel:
    """测试OpenAIGenerationModel"""
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_model_initialization(self, mock_openai_client):
        """测试OpenAI生成模型初始化"""
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
        """测试成功的文本生成"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # 模拟ChatCompletion响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="这是生成的回复"))]
        mock_response.usage = MagicMock(
            prompt_tokens=15,
            completion_tokens=25,
            total_tokens=40
        )
        mock_client.chat.completions.create.return_value = mock_response
        
        model = OpenAIGenerationModel(api_key="test-key")
        prompt = "请回答问题"
        result = model.generate(prompt, temperature=0.8, max_tokens=256)
        
        # 验证API调用
        mock_client.chat.completions.create.assert_called_once_with(
            model=model.model_name,
            messages=[
                {"role": "system", "content": "您是一个有用的AI助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=256,
            top_p=1.0
        )
        
        # 验证结果
        assert isinstance(result, GenerationResult)
        assert result.text == "这是生成的回复"
        assert result.model == model.model_name
        assert result.prompt_tokens == 15
        assert result.completion_tokens == 25
        assert result.total_tokens == 40
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_structured(self, mock_openai_client):
        """测试结构化输出生成"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"result": "结构化数据"}'))]
        mock_response.usage = MagicMock(
            prompt_tokens=20,
            completion_tokens=30,
            total_tokens=50
        )
        mock_client.chat.completions.create.return_value = mock_response
        
        model = OpenAIGenerationModel(api_key="test-key")
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        result = model.generate_structured("生成JSON", schema)
        
        # 验证API调用
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["response_format"] == {"type": "json_object"}
        
        # 验证结果
        assert result.text == '{"result": "结构化数据"}'
        assert result.metadata["schema"] == schema
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_generation_api_error(self, mock_openai_client):
        """测试生成API错误处理"""
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        mock_client.chat.completions.create.side_effect = Exception("API限制")
        
        model = OpenAIGenerationModel(api_key="test-key")
        
        with pytest.raises(Exception) as exc_info:
            model.generate("测试提示")
        
        assert "API限制" in str(exc_info.value)


class TestOpenAIModelFactory:
    """测试OpenAIModelFactory"""
    
    @patch('text2mem.services.models_service_openai.OpenAIEmbeddingModel')
    def test_create_embedding_model(self, mock_embedding_model):
        """测试创建嵌入模型"""
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
        """测试创建嵌入模型时提供商不匹配"""
        config = MagicMock()
        config.embedding_provider = "ollama"
        
        with pytest.raises(ValueError) as exc_info:
            OpenAIModelFactory.create_embedding_model(config)
        
        assert "配置不是OpenAI嵌入模型" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_openai.OpenAIGenerationModel')
    def test_create_generation_model(self, mock_generation_model):
        """测试创建生成模型"""
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
    """测试OpenAI集成功能"""
    
    @patch('text2mem.services.models_service_openai.OpenAIModelFactory')
    @patch('text2mem.services.models_service_openai.ModelsService')
    def test_create_openai_models_service(self, mock_models_service, mock_factory):
        """测试创建OpenAI模型服务"""
        config = MagicMock()
        mock_embed_model = MagicMock()
        mock_gen_model = MagicMock()
        
        mock_factory.create_embedding_model.return_value = mock_embed_model
        mock_factory.create_generation_model.return_value = mock_gen_model
        
        result = create_openai_models_service(config)
        
        # 验证工厂调用
        mock_factory.create_embedding_model.assert_called_once_with(config)
        mock_factory.create_generation_model.assert_called_once_with(config)
        
        # 验证服务创建
        mock_models_service.assert_called_once_with(
            embedding_model=mock_embed_model,
            generation_model=mock_gen_model
        )
    
    @patch('text2mem.services.models_service_openai.HAS_OPENAI', True)
    @patch('text2mem.services.models_service_openai.OpenAI')
    def test_openai_models_environment_variables(self, mock_openai_client):
        """测试从环境变量读取配置"""
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
        """测试并发使用模型"""
        import threading
        import time
        
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client
        
        # 模拟慢响应
        def slow_embedding_response(*args, **kwargs):
            time.sleep(0.1)
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2])]
            mock_response.usage.total_tokens = 5
            return mock_response
        
        def slow_generation_response(*args, **kwargs):
            time.sleep(0.1)
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content="回复"))]
            mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=10, total_tokens=15)
            return mock_response
        
        mock_client.embeddings.create.side_effect = slow_embedding_response
        mock_client.chat.completions.create.side_effect = slow_generation_response
        
        embed_model = OpenAIEmbeddingModel(api_key="test-key")
        gen_model = OpenAIGenerationModel(api_key="test-key")
        
        results = []
        
        def embed_task():
            result = embed_model.embed_text("测试")
            results.append(("embed", result))
        
        def gen_task():
            result = gen_model.generate("测试")
            results.append(("gen", result))
        
        # 启动并发任务
        threads = [
            threading.Thread(target=embed_task),
            threading.Thread(target=gen_task)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证结果
        assert len(results) == 2
        result_types = [r[0] for r in results]
        assert "embed" in result_types
        assert "gen" in result_types
