"""
Unit tests for text2mem.adapters.base module.
Focus areas:
1. ExecutionResult data structure
2. BaseAdapter abstract interface
3. Error handling mechanism
"""
import pytest
from unittest.mock import Mock, patch
from text2mem.adapters.base import BaseAdapter, ExecutionResult
from text2mem.core.models import IR


class TestExecutionResult:
    """Tests for the ExecutionResult data class."""
    
    def test_execution_result_success(self):
        """Test successful execution result."""
        result = ExecutionResult(success=True, data={"id": "mem123"})
        assert result.success is True
        assert result.data == {"id": "mem123"}
        assert result.error is None
        assert result.meta is None
        
        # Boolean conversion should be True for success
        assert bool(result) is True
    
    def test_execution_result_failure(self):
        """Test failed execution result."""
        result = ExecutionResult(success=False, error="Database connection failed")
        assert result.success is False
        assert result.data is None
        assert result.error == "Database connection failed"
        
        # Boolean conversion should be False for failure
        assert bool(result) is False
    
    def test_execution_result_with_meta(self):
        """Test execution result with metadata."""
        meta = {"execution_time": 0.123, "sql": "SELECT * FROM memories"}
        result = ExecutionResult(success=True, data=[], meta=meta)
        assert result.meta == meta
        assert result.meta["execution_time"] == 0.123
    
    def test_execution_result_truthiness(self):
        """Test truthiness behavior of ExecutionResult."""
        # Success results evaluate to True
        assert ExecutionResult(success=True)
        assert ExecutionResult(success=True, data=None)
        assert ExecutionResult(success=True, data=[])
        
        # Failed results evaluate to False
        assert not ExecutionResult(success=False)
        assert not ExecutionResult(success=False, error="Error")


class MockAdapter(BaseAdapter):
    """Mock adapter implementation for testing BaseAdapter behavior."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.executed_operations = []
    
    def execute(self, ir: IR) -> ExecutionResult:
        """Simulate IR operation execution."""
        self.executed_operations.append(ir)
        
        if self.should_fail:
            return ExecutionResult(
                success=False, 
                error=f"Simulated execution failure: {ir.op}"
            )
        
        # Return mock results based on operation type
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
                    {"id": "mem123", "text": "Test memory 1"},
                    {"id": "mem456", "text": "Test memory 2"}
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
        """Simulate closing the adapter connection."""
        pass


class TestBaseAdapter:
    """Tests for BaseAdapter abstract class."""
    
    def test_base_adapter_is_abstract(self):
        """BaseAdapter should be abstract and not instantiable."""
        with pytest.raises(TypeError):
            BaseAdapter()
    
    def test_mock_adapter_execute_encode(self):
        """Test mock adapter executing an Encode operation."""
        adapter = MockAdapter()
        ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "Test text"}})
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert result.data["id"] == "mem123"
        assert "embedding" in result.data
        assert result.meta["operation"] == "encode"
        assert len(adapter.executed_operations) == 1
        assert adapter.executed_operations[0] == ir
    
    def test_mock_adapter_execute_retrieve(self):
        """Test mock adapter executing a Retrieve operation."""
        adapter = MockAdapter()
        ir = IR(stage="RET", op="Retrieve", target={"ids": ["mem123"]}, args={})
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["id"] == "mem123"
        assert result.meta["count"] == 2
    
    def test_mock_adapter_execute_update(self):
        """Test mock adapter executing an Update operation."""
        adapter = MockAdapter()
        ir = IR(stage="STO", op="Update", target={"ids": "mem123"}, args={"set": {"text": "Test text"}})
        
        result = adapter.execute(ir)
        
        assert result.success is True
        assert result.data["updated_count"] == 1
        assert result.meta["operation"] == "update"
    
    def test_mock_adapter_failure_handling(self):
        """Test failure handling in the mock adapter."""
        adapter = MockAdapter(should_fail=True)
        ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "Test text"}})
        
        result = adapter.execute(ir)
        
        assert result.success is False
        assert result.data is None
        assert "Simulated execution failure: Encode" in result.error
        assert not result  # Boolean conversion
    
    def test_adapter_close_method(self):
        """Test adapter close() method does not raise errors."""
        adapter = MockAdapter()
        adapter.close()
    
    def test_execution_result_chaining(self):
        """Test chaining multiple executions using the adapter."""
        adapter = MockAdapter()
        encode_ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "Text1"}})
        retrieve_ir = IR(stage="RET", op="Retrieve", target={"ids": ["mem123"]}, args={})

        encode_result = adapter.execute(encode_ir)
        retrieve_result = adapter.execute(retrieve_ir)

        # Verify execution history
        assert len(adapter.executed_operations) == 2
        assert adapter.executed_operations[0].op == "Encode"
        assert adapter.executed_operations[1].op == "Retrieve"

        # Verify independent results
        assert encode_result.data["id"] == "mem123"
        assert len(retrieve_result.data) == 2
        assert encode_result.meta["operation"] != retrieve_result.meta["operation"]


class TestAdapterIntegration:
    """Integration tests for adapter behavior."""
    
    def test_adapter_with_different_ir_types(self):
        """Test adapter handling multiple IR operation types."""
        adapter = MockAdapter()
        
        operations = [
            ("ENC", "Encode", {"payload": {"text": "Encoding test"}}, None),
            ("RET", "Retrieve", {}, {"ids": ["mem123"]}),
            ("STO", "Update", {"set": {"text": "Update test"}}, {"ids": ["mem123"]}),
            ("STO", "Delete", {"soft": True}, {"ids": ["mem123"]}),
            ("STO", "Label", {"tags": ["test"]}, {"ids": ["mem123"]}),
            ("RET", "Summarize", {"focus": "key_points"}, {"ids": ["mem123"]}),
        ]
        
        results = []
        for stage, op, args, target in operations:
            ir = IR(stage=stage, op=op, target=target, args=args)
            result = adapter.execute(ir)
            results.append(result)
        
        # All operations should succeed
        assert all(result.success for result in results)
        assert len(adapter.executed_operations) == len(operations)
    
    def test_adapter_error_consistency(self):
        """Test consistent error handling across operations."""
        failing_adapter = MockAdapter(should_fail=True)
        
        operations = [
            ("ENC", "Encode", None),
            ("RET", "Retrieve", {"ids": ["mem123"]}), 
            ("STO", "Update", {"ids": ["mem123"]}),
            ("STO", "Delete", {"ids": ["mem123"]}),
        ]
        
        for stage, op, target in operations:
            ir = IR(stage=stage, op=op, target=target, args={})
            result = failing_adapter.execute(ir)
            
            assert result.success is False
            assert result.data is None
            assert result.error is not None
            assert op in result.error
            assert not result  # Boolean conversion
    
    def test_execution_result_data_types(self):
        """Test data type variety in execution results."""
        adapter = MockAdapter()
        
        # Encode should return a dict
        encode_ir = IR(stage="ENC", op="Encode", args={"payload": {"text": "test"}})
        encode_result = adapter.execute(encode_ir)
        assert isinstance(encode_result.data, dict)
        
        # Retrieve should return a list
        retrieve_ir = IR(stage="RET", op="Retrieve", target={"ids": ["mem123"]}, args={"k": 5})
        retrieve_result = adapter.execute(retrieve_ir)
        assert isinstance(retrieve_result.data, list)
        
        # Update should return a dict
        update_ir = IR(stage="STO", op="Update", target={"ids": ["mem123"]}, args={"set": {"text": "new"}})
        update_result = adapter.execute(update_ir)
        assert isinstance(update_result.data, dict)
