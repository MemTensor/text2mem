#!/usr/bin/env python3
"""
createText2Memstandard空data库

这个工具create一个standard的空data库，include完整的memory表schema。
用于testor初始化新的data库实例。

Usage:
    # create内存data库（test用）
    python bench/tools/create_empty_db.py
    
    # createfiledata库
    python bench/tools/create_empty_db.py --output /path/to/database.db
    
    # verifyschema
    python bench/tools/create_empty_db.py --verify /path/to/database.db
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# 完整的memory表DDL（与text2mem/adapters/sqlite_adapter.py保持一致）
MEMORY_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Content
    text TEXT,
    type TEXT,

    -- Facets and labels
    subject TEXT,
    time TEXT,
    location TEXT,
    topic TEXT,
    tags TEXT,            -- JSON array
    facets TEXT,          -- JSON object {subject,time,location,topic}

    -- Importance
    weight REAL,

    -- Embedding
    embedding TEXT,       -- JSON array, 原型先存 json
    embedding_dim INTEGER,        -- 嵌入向量维度（用于兼容性检索）
    embedding_model TEXT,         -- 嵌入模型名
    embedding_provider TEXT,      -- 嵌入provide商（ollama/openai/dummy等）

    -- Provenance & lifecycle
    source TEXT,
    auto_frequency TEXT,
    next_auto_update_at TEXT,
    expire_at TEXT,
    expire_action TEXT,
    expire_reason TEXT,

    -- Lock metadata
    lock_mode TEXT,
    lock_reason TEXT,
    lock_policy TEXT,
    lock_expires TEXT,

    -- Lineage (optional for merge/split audits)
    lineage_parents TEXT,    -- JSON array of ancestor IDs
    lineage_children TEXT,   -- JSON array of descendant IDs

    -- Permissions
    read_perm_level TEXT,
    write_perm_level TEXT,
    read_whitelist TEXT,  -- JSON array
    read_blacklist TEXT,
    write_whitelist TEXT,
    write_blacklist TEXT,

    -- Flags
    deleted INTEGER DEFAULT 0
);
"""


def create_empty_db(output_path: str = ":memory:") -> sqlite3.Connection:
    """
    create一个空的Text2Memdata库
    
    Args:
        output_path: data库filepath，defaults to内存data库
        
    Returns:
        sqlite3.Connection: data库连接object
    """
    conn = sqlite3.connect(output_path)
    conn.executescript(MEMORY_TABLE_DDL)
    return conn


def verify_schema(db_path: str) -> bool:
    """
    verifydata库schemawhether正确
    
    Args:
        db_path: data库filepath
        
    Returns:
        bool: Schemawhether正确
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # check表whetherexist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='memory'
        """)
        if not cursor.fetchone():
            print("❌ 错误: memory表不exist")
            return False
        
        # get表结构
        cursor.execute("PRAGMA table_info(memory)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # required的列
        required_columns = {
            'id': 'INTEGER',
            'text': 'TEXT',
            'type': 'TEXT',
            'tags': 'TEXT',
            'facets': 'TEXT',
            'weight': 'REAL',
            'embedding': 'TEXT',
            'embedding_dim': 'INTEGER',
            'embedding_model': 'TEXT',
            'embedding_provider': 'TEXT',
            'deleted': 'INTEGER',
        }
        
        # verify列
        missing = []
        wrong_type = []
        
        for col_name, col_type in required_columns.items():
            if col_name not in columns:
                missing.append(col_name)
            elif columns[col_name] != col_type:
                wrong_type.append(f"{col_name} (期望{col_type}, 实际{columns[col_name]})")
        
        if missing or wrong_type:
            if missing:
                print(f"❌ 缺少列: {', '.join(missing)}")
            if wrong_type:
                print(f"❌ type错误: {', '.join(wrong_type)}")
            return False
        
        print(f"✅ Schemaverifyvia")
        print(f"   - 表: memory")
        print(f"   - 列数: {len(columns)}")
        print(f"   - required列: 全部exist")
        
        # 显示record数
        cursor.execute("SELECT COUNT(*) FROM memory")
        count = cursor.fetchone()[0]
        print(f"   - record数: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ verifyfailed: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="createText2Memstandard空data库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
example:
  # createdata库file
  python bench/tools/create_empty_db.py --output test.db
  
  # verifyexistingdata库
  python bench/tools/create_empty_db.py --verify test.db
  
  # 显示schema
  python bench/tools/create_empty_db.py --show-schema
        """
    )
    
    parser.add_argument(
        '--output', '-o',
        help='输出data库filepath'
    )
    
    parser.add_argument(
        '--verify', '-v',
        metavar='DB_PATH',
        help='verifyexistingdata库的schema'
    )
    
    parser.add_argument(
        '--show-schema',
        action='store_true',
        help='显示完整的表schema'
    )
    
    args = parser.parse_args()
    
    # 显示schema
    if args.show_schema:
        print("=" * 70)
        print("Text2Mem Memory Table Schema")
        print("=" * 70)
        print(MEMORY_TABLE_DDL)
        return 0
    
    # verifydata库
    if args.verify:
        db_path = args.verify
        if not Path(db_path).exists():
            print(f"❌ 错误: file不exist: {db_path}")
            return 1
        
        print(f"verifydata库: {db_path}")
        print("-" * 70)
        success = verify_schema(db_path)
        return 0 if success else 1
    
    # createdata库
    output_path = args.output or ":memory:"
    
    if output_path != ":memory:":
        output_file = Path(output_path)
        if output_file.exists():
            print(f"⚠️  警告: filealreadyexist: {output_path}")
            response = input("whetheroverride? (y/N): ")
            if response.lower() != 'y':
                print("alreadycancel")
                return 1
        
        # Ensure directories exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"createdata库: {output_path}")
    print("-" * 70)
    
    try:
        conn = create_empty_db(output_path)
        
        if output_path == ":memory:":
            print("✅ 内存data库createsuccess")
            print("\n提示: 内存data库在程序退出后会消失")
            print("      Use --output Argscreatefiledata库")
        else:
            print(f"✅ data库createsuccess: {output_path}")
            
            # verifycreate的data库
            conn.close()
            print("\nverifyschema...")
            verify_schema(output_path)
        
        return 0
        
    except Exception as e:
        print(f"❌ createfailed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
