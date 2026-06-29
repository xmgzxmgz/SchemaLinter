"""
Python代码解析器

解析Python代码中的数据库相关引用，包括原生SQL和SQLAlchemy ORM。
"""

import ast
import re
import logging
from typing import List, Dict, Set, Optional, Any
from .base import BaseParser, CodeReference, ReferenceType

logger = logging.getLogger(__name__)

# SQL关键字和函数名 - 全局常量，用于过滤列名提取
_SQL_KEYWORDS = frozenset({
    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'NULL', 'IS',
    'IN', 'LIKE', 'BETWEEN', 'EXISTS', 'INSERT', 'INTO', 'VALUES',
    'UPDATE', 'SET', 'DELETE', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
    'OUTER', 'ON', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT',
    'OFFSET', 'UNION', 'ALL', 'DISTINCT', 'CURRENT_TIMESTAMP',
    'CURRENT_DATE', 'CURRENT_TIME', 'CASE', 'WHEN', 'THEN', 'ELSE',
    'END', 'ASC', 'DESC', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN',
    'COALESCE', 'IF', 'IFNULL', 'NOW', 'CASCADE', 'RESTRICT',
    'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'INDEX', 'UNIQUE',
    'CONSTRAINT', 'CHECK', 'DEFAULT', 'AUTO_INCREMENT', 'SERIAL',
    'TRUE', 'FALSE',
})


class PythonParser(BaseParser):
    """Python代码解析器"""

    def __init__(self, project_path: str, include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None, db_connector_type: str = "raw_sql"):
        """
        初始化Python解析器

        Args:
            project_path: 项目根目录路径
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
            db_connector_type: 数据库连接器类型 (raw_sql, sqlalchemy)
        """
        super().__init__(project_path, include_patterns, exclude_patterns)
        self.db_connector_type = db_connector_type

        # SQL关键字模式
        self.sql_patterns = [
            r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b',
            r'\b(FROM|INTO|SET|WHERE|JOIN|ON|GROUP BY|ORDER BY|HAVING)\b',
            r'\b(TABLE|COLUMN|INDEX|CONSTRAINT)\b'
        ]

        # 表名和列名提取模式
        self.table_pattern = r'\b(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        self.column_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]'

    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.py']

    def parse_file(self, file_path: str) -> List[CodeReference]:
        """解析Python文件"""
        references = []

        try:
            content = self._read_file_content(file_path)

            # 解析AST
            tree = ast.parse(content)

            # 根据连接器类型选择解析方法
            if self.db_connector_type == "sqlalchemy":
                references.extend(self._parse_sqlalchemy_models(tree, file_path, content))

            # 解析原生SQL字符串
            references.extend(self._parse_sql_strings(tree, file_path, content))

        except Exception as e:
            logger.warning("解析Python文件 %s 时出错: %s", file_path, e)

        return references

    def _parse_sql_strings(self, tree: ast.AST, file_path: str, content: str) -> List[CodeReference]:
        """解析原生SQL字符串"""
        references = []

        class SQLStringVisitor(ast.NodeVisitor):
            def __init__(self, parser_instance):
                self.parser = parser_instance
                self.references = []

            # visit_Str removed - using visit_Constant which handles both old and new AST

            def visit_Constant(self, node):
                if isinstance(node.value, str):
                    self._check_sql_string(node)
                self.generic_visit(node)

            def _check_sql_string(self, node):
                if hasattr(node, 'value') and isinstance(node.value, str):
                    sql_content = node.value.strip()

                    # 检查是否包含SQL关键字
                    if self._is_sql_string(sql_content):
                        line_number = node.lineno
                        context = self.parser._get_line_context(content, line_number)

                        # 提取表名和列名（带表别名支持）
                        tables, columns = self._extract_sql_references(sql_content)

                        # 为每个表创建引用
                        for table in tables:
                            self.references.append(CodeReference(
                                file_path=file_path,
                                line_number=line_number,
                                reference_type=ReferenceType.SQL_QUERY,
                                table_name=table,
                                sql_content=sql_content,
                                context=context,
                                details={'query_type': self._get_query_type(sql_content)}
                            ))

                        # 为每个列创建引用
                        for table, column in columns:
                            self.references.append(CodeReference(
                                file_path=file_path,
                                line_number=line_number,
                                reference_type=ReferenceType.COLUMN_REFERENCE,
                                table_name=table,
                                column_name=column,
                                sql_content=sql_content,
                                context=context,
                                details={'query_type': self._get_query_type(sql_content)}
                            ))

            def _is_sql_string(self, content: str) -> bool:
                """检查字符串是否为SQL语句"""
                content_upper = content.upper()
                for pattern in self.parser.sql_patterns:
                    if re.search(pattern, content_upper):
                        return True
                return False

            def _extract_sql_references(self, sql_content: str) -> tuple:
                """从SQL字符串中提取表名和列名，支持多表JOIN的列归属"""
                tables = set()
                columns = []

                # 提取表名（包括别名映射）
                table_matches = re.findall(
                    r'\b(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
                    r'(?:\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?',
                    sql_content, re.IGNORECASE
                )
                alias_map = {}  # alias -> real_table_name
                for real_name, alias in table_matches:
                    tables.add(real_name)
                    if alias:
                        alias_map[alias.lower()] = real_name

                # 提取列名并正确归属到表
                column_matches = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]', sql_content)
                for column in column_matches:
                    if column.upper() not in _SQL_KEYWORDS:
                        # 默认归属到第一个找到的表
                        if tables:
                            columns.append((list(tables)[0], column))

                # 额外提取 table.column 形式的引用
                qualified_refs = re.findall(
                    r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b',
                    sql_content
                )
                for qualifier, col_name in qualified_refs:
                    if qualifier.upper() not in _SQL_KEYWORDS and col_name.upper() not in _SQL_KEYWORDS:
                        real_table = alias_map.get(qualifier.lower(), qualifier)
                        columns.append((real_table, col_name))

                return tables, columns

            def _get_query_type(self, sql_content: str) -> str:
                """获取SQL查询类型"""
                content_upper = sql_content.upper().strip()
                if content_upper.startswith('SELECT'):
                    return 'SELECT'
                elif content_upper.startswith('INSERT'):
                    return 'INSERT'
                elif content_upper.startswith('UPDATE'):
                    return 'UPDATE'
                elif content_upper.startswith('DELETE'):
                    return 'DELETE'
                else:
                    return 'OTHER'

        visitor = SQLStringVisitor(self)
        visitor.visit(tree)
        references.extend(visitor.references)

        return references

    def _parse_sqlalchemy_models(self, tree: ast.AST, file_path: str, content: str) -> List[CodeReference]:
        """解析SQLAlchemy模型定义"""
        references = []

        class SQLAlchemyVisitor(ast.NodeVisitor):
            def __init__(self, parser_instance):
                self.parser = parser_instance
                self.references = []
                self.current_class = None
                self.current_table = None

            def visit_ClassDef(self, node):
                # 检查是否是SQLAlchemy模型类
                if self._is_sqlalchemy_model(node):
                    self.current_class = node.name
                    self.current_table = self._get_table_name(node)

                    # 创建模型引用
                    self.references.append(CodeReference(
                        file_path=file_path,
                        line_number=node.lineno,
                        reference_type=ReferenceType.ORM_MODEL,
                        table_name=self.current_table,
                        context=self.parser._get_line_context(content, node.lineno),
                        details={
                            'model_class': self.current_class,
                            'table_name': self.current_table
                        }
                    ))

                    # 解析字段定义
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            self._parse_column_definition(item, file_path, content)

                self.generic_visit(node)
                self.current_class = None
                self.current_table = None

            def _is_sqlalchemy_model(self, node: ast.ClassDef) -> bool:
                """检查类是否是SQLAlchemy模型"""
                # 检查基类
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ['Model', 'Base']:
                        return True
                    elif isinstance(base, ast.Attribute):
                        if (isinstance(base.value, ast.Name) and
                            base.value.id == 'db' and base.attr == 'Model'):
                            return True

                # 检查是否有__tablename__属性
                for item in node.body:
                    if (isinstance(item, ast.Assign) and
                        len(item.targets) == 1 and
                        isinstance(item.targets[0], ast.Name) and
                        item.targets[0].id == '__tablename__'):
                        return True

                return False

            def _get_table_name(self, node: ast.ClassDef) -> str:
                """获取表名"""
                # 查找__tablename__属性
                for item in node.body:
                    if (isinstance(item, ast.Assign) and
                        len(item.targets) == 1 and
                        isinstance(item.targets[0], ast.Name) and
                        item.targets[0].id == '__tablename__'):

                        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                            return item.value.value

                # 如果没有__tablename__，使用类名的小写形式
                return node.name.lower()

            def _parse_column_definition(self, node: ast.Assign, file_path: str, content: str):
                """解析列定义"""
                if (len(node.targets) == 1 and
                    isinstance(node.targets[0], ast.Name) and
                    isinstance(node.value, ast.Call)):

                    column_name = node.targets[0].id

                    # 检查是否是Column定义
                    if (isinstance(node.value.func, ast.Name) and
                        node.value.func.id == 'Column'):

                        self.references.append(CodeReference(
                            file_path=file_path,
                            line_number=node.lineno,
                            reference_type=ReferenceType.ORM_FIELD,
                            table_name=self.current_table,
                            column_name=column_name,
                            context=self.parser._get_line_context(content, node.lineno),
                            details={
                                'model_class': self.current_class,
                                'field_name': column_name,
                                'table_name': self.current_table
                            }
                        ))

        visitor = SQLAlchemyVisitor(self)
        visitor.visit(tree)
        references.extend(visitor.references)

        return references
