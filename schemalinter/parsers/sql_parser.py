"""
SQL文件解析器

专门解析.sql文件中的数据库引用。
"""

import re
import sqlparse
from typing import List, Set, Tuple
from .base import BaseParser, CodeReference, ReferenceType


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
            
            # 按行解析SQL内容
            lines = content.split('\n')
            
            for line_number, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('--') or line.startswith('/*'):
                    continue
                
                # 解析单行SQL
                line_references = self._parse_sql_line(line, file_path, line_number, content)
                references.extend(line_references)
            
            # 使用sqlparse解析完整的SQL语句
            statements = sqlparse.split(content)
            for statement in statements:
                if statement.strip():
                    stmt_references = self._parse_sql_statement(statement, file_path, content)
                    references.extend(stmt_references)
        
        except Exception as e:
            print(f"警告: 解析SQL文件 {file_path} 时出错: {e}")
        
        return references
    
    def _parse_sql_line(self, line: str, file_path: str, line_number: int, content: str) -> List[CodeReference]:
        """解析单行SQL"""
        references = []
        
        # 提取表名
        tables = self._extract_table_names(line)
        for table in tables:
            references.append(CodeReference(
                file_path=file_path,
                line_number=line_number,
                reference_type=ReferenceType.TABLE_REFERENCE,
                table_name=table,
                sql_content=line,
                context=self._get_line_context(content, line_number),
                details={'query_type': self._get_query_type(line)}
            ))
        
        # 提取列名
        columns = self._extract_column_names(line, tables)
        for table, column in columns:
            references.append(CodeReference(
                file_path=file_path,
                line_number=line_number,
                reference_type=ReferenceType.COLUMN_REFERENCE,
                table_name=table,
                column_name=column,
                sql_content=line,
                context=self._get_line_context(content, line_number),
                details={'query_type': self._get_query_type(line)}
            ))
        
        return references
    
    def _parse_sql_statement(self, statement: str, file_path: str, content: str) -> List[CodeReference]:
        """解析完整的SQL语句"""
        references = []
        
        try:
            parsed = sqlparse.parse(statement)[0]
            
            # 获取语句的起始行号
            line_number = self._get_statement_line_number(statement, content)
            
            # 提取表名和列名
            tables, columns = self._extract_references_from_parsed(parsed)
            
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
            print(f"警告: 解析SQL语句时出错: {e}")
        
        return references
    
    def _extract_table_names(self, sql: str) -> Set[str]:
        """从SQL语句中提取表名"""
        tables = set()
        
        for pattern in self.table_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for match in matches:
                # 清理表名（去除引号等）
                table_name = match.strip().strip('`"[]')
                if table_name and not table_name.upper() in ['SELECT', 'FROM', 'WHERE', 'AND', 'OR']:
                    tables.add(table_name)
        
        return tables
    
    def _extract_column_names(self, sql: str, tables: Set[str]) -> List[Tuple[str, str]]:
        """从SQL语句中提取列名"""
        columns = []
        
        # 简化的列名提取
        for pattern in self.column_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for match in matches:
                if pattern.startswith(r'\bSELECT'):
                    # 处理SELECT子句中的列名
                    column_list = match.split(',')
                    for col in column_list:
                        col = col.strip().split()[0]  # 取第一个词作为列名
                        col = col.strip('`"[]')
                        if col and col != '*' and not col.upper() in ['DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN']:
                            # 假设列属于第一个表（简化处理）
                            if tables:
                                columns.append((list(tables)[0], col))
                else:
                    # 其他模式的列名
                    col = match.strip().strip('`"[]')
                    if col and not col.upper() in ['SELECT', 'FROM', 'WHERE', 'AND', 'OR']:
                        # 假设列属于第一个表（简化处理）
                        if tables:
                            columns.append((list(tables)[0], col))
        
        return columns
    
    def _extract_references_from_parsed(self, parsed) -> Tuple[Set[str], List[Tuple[str, str]]]:
        """从解析后的SQL语句中提取引用"""
        tables = set()
        columns = []
        
        # 递归遍历解析树
        def visit_token(token):
            if token.ttype is sqlparse.tokens.Name:
                # 这是一个简化的实现
                # 实际应用中需要更复杂的逻辑来区分表名和列名
                name = token.value.strip('`"[]')
                if name:
                    tables.add(name)
        
        # 遍历所有token
        for token in parsed.flatten():
            visit_token(token)
        
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