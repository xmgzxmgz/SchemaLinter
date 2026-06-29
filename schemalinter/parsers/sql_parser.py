"""
SQL文件解析器

专门解析.sql文件中的数据库引用。
"""

import re
import logging
import sqlparse
from typing import List, Set, Tuple
from .base import BaseParser, CodeReference, ReferenceType

logger = logging.getLogger(__name__)

# SQL关键字 - 用于过滤列名误提取
_SQL_KEYWORDS = frozenset({
    'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'NULL', 'IS',
    'IN', 'LIKE', 'BETWEEN', 'EXISTS', 'INSERT', 'INTO', 'VALUES',
    'UPDATE', 'SET', 'DELETE', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
    'OUTER', 'ON', 'AS', 'ORDER', 'BY', 'GROUP', 'HAVING', 'LIMIT',
    'OFFSET', 'UNION', 'ALL', 'DISTINCT', 'CURRENT_TIMESTAMP',
    'COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'PRIMARY', 'KEY',
})


class SQLStringParser(BaseParser):
    """SQL文件解析器"""

    def __init__(self, project_path: str, include_patterns: List[str] = None,
                 exclude_patterns: List[str] = None):
        """
        初始化SQL解析器

        Args:
            project_path: 项目根目录路径
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
        """
        super().__init__(project_path, include_patterns, exclude_patterns)

        # SQL表名提取模式
        self.table_patterns = [
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bTABLE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]

        # 列名提取模式
        self.column_patterns = [
            r'\bSELECT\s+(.+?)\s+FROM',
            r'\bSET\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
            r'\bWHERE\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[=<>!]',
            r'\bORDER\s+BY\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'\bGROUP\s+BY\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        ]

    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        return ['.sql']

    def parse_file(self, file_path: str) -> List[CodeReference]:
        """解析SQL文件"""
        references = []

        try:
            content = self._read_file_content(file_path)

            # 使用sqlparse解析完整的SQL语句
            statements = sqlparse.split(content)
            for statement in statements:
                if statement.strip():
                    stmt_references = self._parse_sql_statement(statement, file_path, content)
                    references.extend(stmt_references)

        except Exception as e:
            logger.warning("解析SQL文件 %s 时出错: %s", file_path, e)

        return references

    def _parse_sql_statement(self, statement: str, file_path: str, content: str) -> List[CodeReference]:
        """解析完整的SQL语句"""
        references = []

        try:
            parsed = sqlparse.parse(statement)[0]

            # 获取语句的起始行号
            line_number = self._get_statement_line_number(statement, content)

            # 提取表名和列名（带别名映射）
            tables, columns = self._extract_references_from_parsed(parsed, statement)

            # 创建表引用
            for table in tables:
                references.append(CodeReference(
                    file_path=file_path,
                    line_number=line_number,
                    reference_type=ReferenceType.TABLE_REFERENCE,
                    table_name=table,
                    sql_content=statement.strip(),
                    context=self._get_line_context(content, line_number),
                    details={'query_type': self._get_query_type(statement)}
                ))

            # 创建列引用
            for table, column in columns:
                references.append(CodeReference(
                    file_path=file_path,
                    line_number=line_number,
                    reference_type=ReferenceType.COLUMN_REFERENCE,
                    table_name=table,
                    column_name=column,
                    sql_content=statement.strip(),
                    context=self._get_line_context(content, line_number),
                    details={'query_type': self._get_query_type(statement)}
                ))

        except Exception as e:
            logger.warning("解析SQL语句时出错: %s", e)

        return references

    def _extract_references_from_parsed(self, parsed, raw_sql: str) -> Tuple[Set[str], List[Tuple[str, str]]]:
        """从解析后的SQL语句中提取引用，带表别名支持"""
        tables = set()
        columns = []

        # 构建别名映射: alias -> real_table
        alias_map = {}
        alias_matches = re.findall(
            r'(?:FROM|INTO|UPDATE|JOIN)\s+(\w+)(?:\s+(?:AS\s+)?(\w+))?',
            raw_sql, re.IGNORECASE
        )
        for real_name, alias in alias_matches:
            tables.add(real_name)
            if alias and alias.upper() not in _SQL_KEYWORDS:
                alias_map[alias.lower()] = real_name

        # 提取 table.column 形式的限定列引用
        qualified = re.findall(
            r'\b(\w+)\.(\w+)\b',
            raw_sql
        )
        for qualifier, col_name in qualified:
            if (qualifier.upper() not in _SQL_KEYWORDS and
                col_name.upper() not in _SQL_KEYWORDS):
                real_table = alias_map.get(qualifier.lower(), qualifier)
                columns.append((real_table, col_name))

        # 提取简单列名（非限定）
        simple_col_patterns = [
            r'\bSET\s+(\w+)\s*=',
            r'\bWHERE\s+(\w+)\s*[=<>!]',
            r'\bORDER\s+BY\s+(\w+)',
            r'\bGROUP\s+BY\s+(\w+)',
        ]
        for pattern in simple_col_patterns:
            for match in re.findall(pattern, raw_sql, re.IGNORECASE):
                if match.upper() not in _SQL_KEYWORDS:
                    # 归属到第一个找到的表
                    if tables:
                        columns.append((list(tables)[0], match))

        # 处理 SELECT 列列表（去重已有 qualified 的）
        select_match = re.search(r'\bSELECT\s+(.+?)\s+FROM\b', raw_sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_body = select_match.group(1)
            select_cols = [c.strip() for c in select_body.split(',')]
            for col_expr in select_cols:
                # 跳过 table.column 形式 (已在上面处理)
                if '.' in col_expr:
                    continue
                # 取第一个 token 作为列名
                col_token = col_expr.split()[0].strip('`"[]')
                if col_token == '*' or col_token.upper() in _SQL_KEYWORDS:
                    continue
                # 检查是否有别名 (AS)
                parts = col_expr.split()
                if len(parts) >= 3 and parts[1].upper() == 'AS':
                    col_token = parts[0].strip('`"[]')
                if col_token and col_token != '*' and col_token.upper() not in _SQL_KEYWORDS:
                    if tables:
                        columns.append((list(tables)[0], col_token))

        return tables, columns

    def _get_statement_line_number(self, statement: str, content: str) -> int:
        """获取语句在文件中的行号"""
        lines = content.split('\n')
        statement_start = statement.strip()[:50]  # 取前50个字符进行匹配

        for i, line in enumerate(lines, 1):
            if statement_start in line:
                return i

        return 1

    def _get_query_type(self, sql: str) -> str:
        """获取SQL查询类型"""
        sql_upper = sql.upper().strip()

        if sql_upper.startswith('SELECT'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        elif sql_upper.startswith('CREATE'):
            return 'CREATE'
        elif sql_upper.startswith('ALTER'):
            return 'ALTER'
        elif sql_upper.startswith('DROP'):
            return 'DROP'
        else:
            return 'OTHER'
