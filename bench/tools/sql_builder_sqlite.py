"""
SQL Builder for SQLite Assertions

编译test断言为SQLquery
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional


@dataclass
class CompiledAssertion:
    """编译后的断言"""
    name: str
    sql: str
    params: Dict[str, Any]
    expectation: Tuple[str, Any]  # (operator, expected_value)


class SQLiteAssertionCompiler:
    """will断言规范编译为SQLquery"""
    
    def compile(self, spec: Dict[str, Any]) -> CompiledAssertion:
        """
        编译断言规范
        
        支持两种format：
        1. 旧format（扁平）:
            {
                "name": "record_created",
                "from_table": "memory",
                "where": ["deleted=0"],
                "expect_op": ">=",
                "expect_value": 1,
                "params": {"keyword": "%test%"}
            }
        
        2. 新format（嵌套）:
            {
                "name": "record_created",
                "select": {
                    "from": "memory",
                    "where": ["deleted=0"],
                    "agg": "count"
                },
                "expect": {
                    "op": ">=",
                    "value": 1
                },
                "params": {"keyword": "%test%"}
            }
        
        Returns:
            CompiledAssertion: 编译后的断言
        """
        name = spec.get("name", "unnamed_assertion")
        params = spec.get("params", {})
        
        # checkUse新format还是旧format
        if "select" in spec:
            # 新format
            select_spec = spec["select"]
            table = select_spec.get("from", "memory")
            where_clauses = select_spec.get("where", [])
            # agg字段暂时ignore，defaultUseCOUNT(*)
            
            expect_spec = spec.get("expect", {})
            expect_op = expect_spec.get("op", "==")
            expect_value = expect_spec.get("value")
        else:
            # 旧format（向后兼容）
            table = spec.get("from_table", "memory")
            where_clauses = spec.get("where", [])
            expect_op = spec.get("expect_op", "==")
            expect_value = spec.get("expect_value")
        
        # buildSQL
        sql = f"SELECT COUNT(*) as actual FROM {table}"
        
        if where_clauses:
            where_str = " AND ".join(f"({clause})" for clause in where_clauses)
            sql += f" WHERE {where_str}"
        
        expectation = (expect_op, expect_value)
        
        return CompiledAssertion(
            name=name,
            sql=sql,
            params=params,
            expectation=expectation
        )


def evaluate_expectation(expectation: Tuple[str, Any], actual: Any) -> Tuple[bool, str]:
    """
    评估期望值
    
    Args:
        expectation: (operator, expected_value)
        actual: 实际值
        
    Returns:
        (success, message)
    """
    op, expected = expectation
    
    try:
        if op == "==":
            success = actual == expected
        elif op == "!=":
            success = actual != expected
        elif op == ">":
            success = actual > expected
        elif op == ">=":
            success = actual >= expected
        elif op == "<":
            success = actual < expected
        elif op == "<=":
            success = actual <= expected
        else:
            return False, f"Unknown operator: {op}"
        
        if success:
            message = f"actual={actual} {op} expected={expected} -> PASS"
        else:
            message = f"actual={actual} {op} expected={expected} -> FAIL"
        
        return success, message
        
    except Exception as e:
        return False, f"Error: {str(e)}"
