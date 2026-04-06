"""
数据库服务层
提供简化的数据库访问接口
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from infra.logs.logger_config import get_logger

logger = get_logger("services.db_service")


class DatabaseService:
    """数据库服务类"""
    
    def __init__(self):
        # 数据库文件路径 - 放在 data 目录下
        self.db_path = Path(__file__).parent.parent / "data" / "demo.db"
        logger.info(f"Database path: {self.db_path}")
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询并返回结果
        
        :param sql: SQL语句
        :param params: 参数元组
        :return: 查询结果列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            result = cursor.fetchall()
            conn.close()
            
            # 将Row对象转换为字典
            return [dict(row) for row in result]
            
        except Exception as e:
            logger.error(f"SQL执行失败: {sql}, 错误: {e}")
            return []
    
    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行更新操作并返回影响的行数
        
        :param sql: SQL语句
        :param params: 参数元组
        :return: 影响的行数
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"更新操作成功，影响 {affected_rows} 行")
            return affected_rows
            
        except Exception as e:
            logger.error(f"更新操作失败: {sql}, 错误: {e}")
            return 0
    
    def execute_insert(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        执行插入操作并返回插入的ID
        
        :param sql: SQL语句
        :param params: 参数元组
        :return: 插入记录的ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            
            insert_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"插入操作成功，ID: {insert_id}")
            return insert_id
            
        except Exception as e:
            logger.error(f"插入操作失败: {sql}, 错误: {e}")
            return 0
    
    def initialize_database(self) -> bool:
        """
        初始化数据库表结构
        """
        logger.info("开始初始化数据库...")
        
        # 创建表的SQL语句
        create_tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS deduction_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                deduction_points INTEGER NOT NULL,
                sequence INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES assessment_categories(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS assessment_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                deduction_rule_id INTEGER NOT NULL,
                record_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                remarks TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id),
                FOREIGN KEY (category_id) REFERENCES assessment_categories(id),
                FOREIGN KEY (deduction_rule_id) REFERENCES deduction_rules(id)
            )
            """
        ]
        
        try:
            for sql in create_tables_sql:
                self.execute_update(sql)
            
            logger.info("数据库表结构初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            return False


# 全局数据库服务实例
db_service = DatabaseService()
