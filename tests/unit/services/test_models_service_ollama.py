"""
测试 text2mem.services.models_service_ollama 模块
重点测试：
1. Ollama模型的初始化和配置
2. 网络请求处理
3. 错误处理和重试机制
4. 响应解析
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import threading
import time
from text2mem.services.models_service_ollama import OllamaEmbeddingModel, OllamaGenerationModel
from text2mem.services.models_service import EmbeddingResult, GenerationResult


class TestOllamaEmbeddingModel:
    """测试OllamaEmbeddingModel"""
    
    def test_ollama_embedding_model_initialization(self):
        """测试Ollama嵌入模型初始化"""
        model = OllamaEmbeddingModel(
            model_name="nomic-embed-text",
            base_url="http://localhost:11434"
        )
        
        assert model.model_name == "nomic-embed-text"
        assert model.base_url == "http://localhost:11434"
        assert hasattr(model, 'client')
        assert model.get_dimension() == 768

    def test_ollama_embedding_default_dimension_unknown_model(self):
        """未知模型名时应返回默认维度 768"""
        model = OllamaEmbeddingModel(model_name="some-unknown-embedder")
        assert model.get_dimension() == 768
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_success(self, mock_client_class):
        """测试成功的嵌入请求"""
        # 模拟httpx.Client实例
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        # 模拟成功响应
        mock_response = Mock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3, 0.4]}
        mock_client.post.return_value = mock_response
        # 执行
        model = OllamaEmbeddingModel("nomic-embed-text")
        text = "测试文本"
        result = model.embed_text(text)
        # 验证请求参数
        mock_client.post.assert_called_once_with(
            f"{model.base_url}/api/embeddings",
            json={"model": model.model_name, "prompt": text},
        )
        # 验证结果
        assert isinstance(result, EmbeddingResult)
        assert result.embedding == [0.1, 0.2, 0.3, 0.4]
        assert result.model == model.model_name
        assert result.text == text
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_http_error(self, mock_client_class):
        """测试HTTP错误处理"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟HTTP错误
        mock_client.post.side_effect = Exception("HTTP 500")
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception) as exc_info:
            model.embed_text("测试文本")
        
        assert "HTTP 500" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_network_error(self, mock_client_class):
        """测试网络错误处理"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟网络错误
        mock_client.post.side_effect = Exception("连接失败")
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception) as exc_info:
            model.embed_text("测试文本")
        
        assert "连接失败" in str(exc_info.value)
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_embedding_invalid_response(self, mock_client_class):
        """测试无效响应处理"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟无效JSON响应
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_client.post.return_value = mock_response
        
        model = OllamaEmbeddingModel("nomic-embed-text")
        
        with pytest.raises(Exception):
            model.embed_text("测试文本")


class TestOllamaGenerationModel:
    """测试OllamaGenerationModel"""
    
    def test_ollama_generation_model_initialization(self):
        """测试Ollama生成模型初始化"""
        model = OllamaGenerationModel(
            model_name="qwen2:0.5b",
            base_url="http://localhost:11434"
        )
        
        assert model.model_name == "qwen2:0.5b"
        assert model.base_url == "http://localhost:11434"
        assert hasattr(model, 'client')
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_success(self, mock_client_class):
        """测试成功的生成请求"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟成功响应
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "这是生成的回复文本",
            "done": True
        }
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        prompt = "请回答问题"
        result = model.generate(prompt)
        
        # 验证请求参数
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == f"{model.base_url}/api/generate"
        
        request_data = call_args[1]['json']
        assert request_data['model'] == model.model_name
        assert request_data['prompt'] == prompt
        assert request_data['stream'] is False
        
        # 验证结果
        assert isinstance(result, GenerationResult)
        assert result.text == "这是生成的回复文本"
        assert result.model == model.model_name
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_with_options(self, mock_client_class):
        """测试带选项的生成请求"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "回复",
            "done": True
        }
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        model.generate("测试提示", temperature=0.8, max_tokens=256)
        
        # 验证选项参数
        call_args = mock_client.post.call_args
        request_data = call_args[1]['json']
        
        assert 'options' in request_data
        options = request_data['options']
        assert options['temperature'] == 0.8
        assert options['num_predict'] == 256
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_incomplete_response(self, mock_client_class):
        """测试不完整响应处理"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟不完整响应（done=False）
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "部分回复",
            "done": False
        }
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        result = model.generate("测试提示")
        
        # 应该能处理不完整的响应
        assert result.text == "部分回复"
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_generation_missing_response_field(self, mock_client_class):
        """测试缺少response字段的情况"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "done": True
            # 缺少response字段
        }
        mock_client.post.return_value = mock_response
        
        model = OllamaGenerationModel("qwen2:0.5b")
        
        with pytest.raises(Exception):
            model.generate("测试提示")


class TestOllamaIntegration:
    """测试Ollama服务集成"""
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_models_with_same_base_url(self, mock_client_class):
        """测试使用相同base_url的模型"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 配置不同的响应
        def side_effect(*args, **kwargs):
            mock_response = Mock()
            
            if "embeddings" in args[0]:
                mock_response.json.return_value = {
                    "embedding": [0.1, 0.2, 0.3]
                }
            else:  # generate
                mock_response.json.return_value = {
                    "response": "生成的文本",
                    "done": True
                }
            
            return mock_response
        
        mock_client.post.side_effect = side_effect
        
        base_url = "http://localhost:11434"
        embed_model = OllamaEmbeddingModel("nomic-embed-text", base_url=base_url)
        gen_model = OllamaGenerationModel("qwen2:0.5b", base_url=base_url)
        
        # 测试两个模型都能正常工作
        embed_result = embed_model.embed_text("测试")
        gen_result = gen_model.generate("测试")
        
        assert embed_result.embedding == [0.1, 0.2, 0.3]
        assert gen_result.text == "生成的文本"
        
        # 验证调用了正确的端点
        assert mock_client.post.call_count == 2
        calls = [call[0][0] for call in mock_client.post.call_args_list]
        assert f"{base_url}/api/embeddings" in calls
        assert f"{base_url}/api/generate" in calls
    
    def test_ollama_models_different_timeouts(self):
        """测试不同超时设置的模型"""
        embed_model = OllamaEmbeddingModel("nomic-embed-text")
        gen_model = OllamaGenerationModel("qwen2:0.5b")
        
        # 验证模型初始化成功
        assert embed_model.model_name == "nomic-embed-text"
        assert gen_model.model_name == "qwen2:0.5b"

    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_clients_timeouts(self, mock_client_class):
        """验证 httpx.Client 分别以不同超时创建（嵌入60s，生成120s）"""
        embed_client = MagicMock()
        gen_client = MagicMock()
        # 两次实例化按顺序返回不同的client
        mock_client_class.side_effect = [embed_client, gen_client]

        OllamaEmbeddingModel("nomic-embed-text")
        OllamaGenerationModel("qwen2:0.5b")

        calls = mock_client_class.call_args_list
        assert len(calls) == 2
        # 第一次为嵌入模型
        assert calls[0].kwargs.get('timeout') == 60.0
        # 第二次为生成模型
        assert calls[1].kwargs.get('timeout') == 120.0
    
    @patch('text2mem.services.models_service_ollama.httpx.Client')
    def test_ollama_models_concurrent_requests(self, mock_client_class):
        """测试并发请求处理"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # 模拟慢响应
        def slow_response(*args, **kwargs):
            time.sleep(0.1)  # 模拟网络延迟
            mock_response = Mock()
            if "embeddings" in args[0]:
                mock_response.json.return_value = {"embedding": [0.1, 0.2]}
            else:
                mock_response.json.return_value = {"response": "回复", "done": True}
            return mock_response
        
        mock_client.post.side_effect = slow_response
        
        embed_model = OllamaEmbeddingModel("nomic-embed-text")
        gen_model = OllamaGenerationModel("qwen2:0.5b")
        
        results = []
        
        def embed_task():
            result = embed_model.embed_text("测试")
            results.append(("embed", result))
        
        def gen_task():
            result = gen_model.generate("测试")
            results.append(("gen", result))
        
        # 启动并发请求
        threads = [
            threading.Thread(target=embed_task),
            threading.Thread(target=gen_task)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 验证两个请求都成功完成
        assert len(results) == 2
        result_types = [r[0] for r in results]
        assert "embed" in result_types
        assert "gen" in result_types
