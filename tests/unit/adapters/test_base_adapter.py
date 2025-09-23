"""
测试 text2mem.adapters.base 模块中的基础适配器类
重点测试：
1. ExecutionResult 数据结构
2. BaseAdapter 抽象接口
3. 错误处理机制
"""
import pytest
from unittest.mock import Mock, patch
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.core.models import IR


class TestExecutionResult:
    """测试ExecutionResult执行结果类"""
    
    def test_execution_result_success(self):
        """测试成功的执行结果"""
        result = ExecutionResult(success=True, data={"id": "mem123"})
        assert result.success is True
        assert result.data == {"id": "mem123"}
        assert result.error is None
        assert result.meta is None
        
        # 测试布尔转换
        assert bool(result) is True
    
    def test_execution_result_failure(self):
        """测试失败的执行结果"""
        result = ExecutionResult(success=False, error="数据库连接失败")
        assert result.success is False
        assert result.data is None
        assert result.error == "数据库连接失败"
        
        # 测试布尔转换
        assert bool(result) is False
    
    def test_execution_result_with_meta(self):
        """测试带元数据的执行结果"""
        meta = {"execution_time": 0.123, "sql": "SELECT * FROM memories"}
        result = ExecutionResult(
            success=True, 
            data=[], 
            meta=meta
        )
        assert result.meta == meta
        assert result.meta["execution_time"] == 0.123
    
    def test_execution_result_truthiness(self):
        """测试ExecutionResult的真值表现"""
        # 成功结果为真
        assert ExecutionResult(success=True)
        assert ExecutionResult(success=True, data=None)
        assert ExecutionResult(success=True, data=[])
        
        # 失败结果为假
        assert not ExecutionResult(success=False)
        assert not ExecutionResult(success=False, error="错误")


class MockAdapter(BaseAdapter):
    """用于测试的模拟适配器实现"""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.executed_operations = []
    
    def execute(self, ir: IR) -> ExecutionResult:
        """模拟执行IR操作"""
        self.executed_operations.append(ir)
        
        if self.should_fail:
            return ExecutionResult(
                success=False, 
                error=f"模拟执行失败: {ir.op}"
            )
        
        # 根据操作类型返回不同的模拟结果
        if ir.op == "Encode":
            return ExecutionResult(
                success=True,
                data={"id": "mem123", "embedding": [0.1, 0.2, 0.3]},
                meta={"operation": "encode", "timestamp": "2023-12-01T10:30:00Z"}
            )
        elif ir.op == "Retrieve":
            return ExecutionResult(
                success=True,
                data=[
                    {"id": "mem123", "text": "测试记忆1"},
                    {"id": "mem456", "text": "测试记忆2"}
                ],
                meta={"count": 2, "operation": "retrieve"}
            )
        elif ir.op == "Update":
            return ExecutionResult(
                success=True,
                data={"updated_count": 1},
                meta={"operation": "update"}
            )
        else:
            return ExecutionResult(
                success=True,
                data={"operation": ir.op.lower()},
                meta={"operation": ir.op.lower()}
            )
    
    def close(self):
        """模拟关闭连接"""
        pass


class TestBaseAdapter:
    """测试BaseAdapter基础适配器类"""
    
    def test_base_adapter_is_abstract(self):
        """测试BaseAdapter是抽象类，不能直接实例化"""
        with pytest.raises(TypeError):
            BaseAdapter()
    
    def test_mock_adapter_execute_encode(self):
        """测试模拟适配器执行Encode操作"""
        adapter = MockAdapter()
        ir = IR(
            stage="ENC",
            op="Encode",
            args={"payload": {"text": "测试文本"}}
        )
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert result.data["id"] == "mem123"
        assert "embedding" in result.data
        assert result.meta["operation"] == "encode"
        assert len(adapter.executed_operations) == 1
        assert adapter.executed_operations[0] == ir
    
    def test_mock_adapter_execute_retrieve(self):
        """测试模拟适配器执行Retrieve操作"""
        adapter = MockAdapter()
        ir = IR(
            stage="RET",
            op="Retrieve",
            args={}
        )
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["id"] == "mem123"
        assert result.meta["count"] == 2
    
    def test_mock_adapter_execute_update(self):
        """测试模拟适配器执行Update操作"""
        adapter = MockAdapter()
        ir = IR(
            stage="STO",
            op="Update",
            target={"ids": "mem123"},
            args={"set": {"text": "测试文本"}}
        )
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert result.data["updated_count"] == 1
        assert result.meta["operation"] == "update"
    
    def test_mock_adapter_failure_handling(self):
        """测试模拟适配器的失败处理"""
        adapter = MockAdapter(should_fail=True)
        ir = IR(
            stage="ENC",
            op="Encode",
            args={"payload": {"text": "测试文本"}}
        )
        
        result = adapter.execute(ir)
        
        assert result.success is False
        assert result.data is None
        assert "模拟执行失败: Encode" in result.error
        assert not result  # 测试布尔转换
    
    def test_adapter_close_method(self):
        """测试适配器的关闭方法"""
        adapter = MockAdapter()
        # 应该能够正常调用close方法而不抛出异常
        adapter.close()
    
    def test_execution_result_chaining(self):
        """测试执行结果的链式处理"""
    adapter = MockAdapter()
    # 执行多个操作
    encode_ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "文本1"}})
    retrieve_ir = IR(stage="RET", op="Retrieve", args={})

    encode_result = adapter.execute(encode_ir)
    retrieve_result = adapter.execute(retrieve_ir)

    # 验证执行历史
    assert len(adapter.executed_operations) == 2
    assert adapter.executed_operations[0].op == "Encode"
    assert adapter.executed_operations[1].op == "Retrieve"

    # 验证结果独立性
    assert encode_result.data["id"] == "mem123"
    assert len(retrieve_result.data) == 2
    assert encode_result.meta["operation"] != retrieve_result.meta["operation"]


class TestAdapterIntegration:
    """测试适配器集成场景"""
    
    def test_adapter_with_different_ir_types(self):
        """测试适配器处理不同类型的IR"""
        adapter = MockAdapter()
        
        # 测试各种操作类型
        operations = [
            ("ENC", "Encode", {"payload": {"text": "编码测试"}}),
            ("RET", "Retrieve", {}),
            ("STO", "Update", {"set": {"text": "更新测试"}}),
            ("STO", "Delete", {"soft": True}),
            ("STO", "Label", {"tags": ["test"]}),
            ("RET", "Summarize", {"focus": "key_points"})
        ]
        
        results = []
        for stage, op, args in operations:
            ir = IR(stage=stage, op=op, args=args)
            result = adapter.execute(ir)
            results.append(result)
        
        # 验证所有操作都成功执行
        assert all(result.success for result in results)
        assert len(adapter.executed_operations) == len(operations)
    
    def test_adapter_error_consistency(self):
        """测试适配器错误处理的一致性"""
        failing_adapter = MockAdapter(should_fail=True)
        
        # 不同操作都应该返回一致的错误格式
        operations = [
            ("ENC", "Encode"),
            ("RET", "Retrieve"), 
            ("STO", "Update"),
            ("STO", "Delete")
        ]
        
        for stage, op in operations:
            ir = IR(stage=stage, op=op, args={})
            result = failing_adapter.execute(ir)
            
            assert result.success is False
            assert result.data is None
            assert result.error is not None
            assert op in result.error
            assert not result  # 测试真值表现
    
    def test_execution_result_data_types(self):
        """测试执行结果数据类型的多样性"""
        adapter = MockAdapter()
        
        # Encode返回字典
        encode_ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "test"}})
        encode_result = adapter.execute(encode_ir)
        assert isinstance(encode_result.data, dict)
        
        # Retrieve返回列表
        retrieve_ir = IR(stage="RET", op="Retrieve", args={"k": 5})
        retrieve_result = adapter.execute(retrieve_ir)
        assert isinstance(retrieve_result.data, list)
        
        # Update返回字典
        update_ir = IR(stage="STO", op="Update", args={"set": {"text": "new"}})
        update_result = adapter.execute(update_ir)
        assert isinstance(update_result.data, dict)
