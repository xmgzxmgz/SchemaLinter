"""
变更识别模块

负责识别数据库结构的变化，生成变更清单。
"""

import re
import logging
import sqlparse
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """变更类型枚举"""
    TABLE_ADDED = "table_added"
    TABLE_DELETED = "table_deleted"
    TABLE_RENAMED = "table_renamed"
    COLUMN_ADDED = "column_added"
    COLUMN_DELETED = "column_deleted"
    COLUMN_RENAMED = "column_renamed"
    COLUMN_TYPE_CHANGED = "column_type_changed"
    INDEX_ADDED = "index_added"
    INDEX_DELETED = "index_deleted"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_DELETED = "constraint_deleted"


@dataclass
class SchemaChange:
    """模式变更记录"""
    change_type: ChangeType
    table_name: str
    old_name: Optional[str] = None
    new_name: Optional[str] = None
    column_name: Optional[str] = None
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class TableSchema:
    """表结构定义"""
    name: str
    columns: Dict[str, str]  # column_name -> column_type
    indexes: Set[str]
    constraints: Set[str]

    def __post_init__(self):
        if not isinstance(self.columns, dict):
            self.columns = {}
        if not isinstance(self.indexes, set):
            self.indexes = set()
        if not isinstance(self.constraints, set):
            self.constraints = set()


class SQLParser:
    """SQL解析器"""

    def __init__(self):
        self.tables: Dict[str, TableSchema] = {}

    def parse_sql_file(self, file_path: str) -> Dict[str, TableSchema]:
        """解析SQL文件，提取表结构"""
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        return self.parse_sql_content(sql_content)

    def parse_sql_content(self, sql_content: str) -> Dict[str, TableSchema]:
        """解析SQL内容并提取表结构"""
        # 重置表字典，避免累积之前的解析结果
        self.tables = {}

        # 使用sqlparse解析SQL语句
        statements = sqlparse.split(sql_content)

        for statement in statements:
            if not statement.strip():
                continue

            parsed = sqlparse.parse(statement)[0]
            self._process_statement(parsed)

        return self.tables

    def _process_statement(self, statement) -> None:
        """处理单个SQL语句"""
        # 获取语句类型
        stmt_type = statement.get_type()

        if stmt_type == 'CREATE':
            self._process_create_statement(statement)
        elif stmt_type == 'ALTER':
            self._process_alter_statement(statement)
        elif stmt_type == 'DROP':
            self._process_drop_statement(statement)

    def _process_create_statement(self, statement) -> None:
        """处理CREATE语句"""
        tokens = list(statement.flatten())

        # 查找CREATE TABLE语句
        for i, token in enumerate(tokens):
            # CREATE关键字可能是Keyword.DDL类型
            if (token.ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL) and
                token.value.upper() == 'CREATE'):
                # 查找下一个关键字
                for j in range(i + 1, len(tokens)):
                    if (tokens[j].ttype in (sqlparse.tokens.Keyword, sqlparse.tokens.Keyword.DDL) and
                        tokens[j].value.strip()):
                        if tokens[j].value.upper() == 'TABLE':
                            self._parse_create_table(tokens, j)
                            break
                        elif tokens[j].value.upper() == 'INDEX':
                            self._parse_create_index(tokens, j)
                            break
                break

    def _parse_create_table(self, tokens: List, start_idx: int) -> None:
        """解析CREATE TABLE语句"""
        # 重新构建语句字符串进行更精确的解析
        statement_str = ''.join(token.value for token in tokens)

        # 匹配CREATE TABLE语句中的列定义部分 - 修复引号匹配
        # 使用贪心匹配 + 末尾 ) 以确保正确捕获含括号的类型如 VARCHAR(200)
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s*\((.+)\)\s*;?\s*$'
        match = re.search(table_pattern, statement_str, re.IGNORECASE | re.DOTALL)

        if not match:
            return

        table_name = match.group(1)
        columns_str = match.group(2)

        # 解析列定义
        columns = {}

        # 分割列定义（处理嵌套的括号）
        column_defs = self._split_column_definitions(columns_str)

        for col_def in column_defs:
            col_def = col_def.strip()
            if not col_def or col_def.upper().startswith(('CONSTRAINT', 'PRIMARY', 'FOREIGN', 'UNIQUE', 'INDEX', 'KEY')):
                continue

            # 解析列名和类型 - 修复 VARCHAR(200 等未闭合括号的问题
            parts = col_def.split(None, 1)
            if len(parts) >= 2:
                col_name = parts[0].strip('`"[]')
                # 提取类型部分（第一个非空格token），处理 VARCHAR(200) 等
                type_match = re.match(
                    r'([A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?)',
                    parts[1],
                    re.IGNORECASE
                )
                if type_match:
                    col_type = type_match.group(1).upper().strip()
                    # 修复未闭合的括号：如果检测到 '(' 但没有 ')'，自动补上
                    if col_type.count('(') > col_type.count(')'):
                        col_type = col_type.rstrip() + ')'
                else:
                    col_type = parts[1].split()[0].upper()
                columns[col_name] = col_type

        # 创建表结构对象
        self.tables[table_name] = TableSchema(
            name=table_name,
            columns=columns,
            indexes=set(),
            constraints=set()
        )

    def _split_column_definitions(self, columns_str: str) -> List[str]:
        """分割列定义，处理嵌套括号"""
        definitions = []
        current_def = ""
        paren_count = 0

        for char in columns_str:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                if current_def.strip():
                    definitions.append(current_def.strip())
                current_def = ""
                continue

            current_def += char

        if current_def.strip():
            definitions.append(current_def.strip())

        return definitions

    def _parse_create_index(self, tokens: List, start_idx: int) -> None:
        """解析CREATE INDEX语句"""
        # 简化的索引解析
        index_name = None
        table_name = None

        for i in range(start_idx + 1, len(tokens)):
            token = tokens[i]
            if token.ttype is None and token.value.strip():
                if index_name is None:
                    index_name = token.value.strip().strip('`"[]')
                elif token.value.upper() == 'ON':
                    # 下一个token应该是表名
                    for j in range(i + 1, len(tokens)):
                        if tokens[j].ttype is None and tokens[j].value.strip():
                            table_name = tokens[j].value.strip().strip('`"[]')
                            break
                    break

        if table_name and index_name and table_name in self.tables:
            self.tables[table_name].indexes.add(index_name)

    def _process_alter_statement(self, statement) -> None:
        """处理ALTER语句 - 识别 ADD/DROP/MODIFY/CHANGE COLUMN, RENAME TABLE 等变更"""
        statement_str = str(statement).strip()

        # 提取表名: ALTER TABLE <table_name>
        table_match = re.search(
            r'ALTER\s+TABLE\s+[`"\']?(\w+)[`"\']?',
            statement_str,
            re.IGNORECASE
        )
        if not table_match:
            return

        table_name = table_match.group(1)
        rest = statement_str[table_match.end():].strip().rstrip(';').strip()
        rest_upper = rest.upper()

        # RENAME TABLE 旧表 -> 新表
        rename_match = re.search(
            r'RENAME\s+(?:TO|AS)\s+[`"\']?(\w+)[`"\']?',
            rest,
            re.IGNORECASE
        )
        if rename_match:
            new_name = rename_match.group(1)
            if table_name in self.tables:
                self.tables[new_name] = self.tables.pop(table_name)
                self.tables[new_name].name = new_name
            else:
                # 如果旧表不在已知列表中，创建一个空表记录
                self.tables[new_name] = TableSchema(
                    name=new_name, columns={}, indexes=set(), constraints=set()
                )
            logger.debug("ALTER RENAME TABLE %s -> %s", table_name, new_name)
            return

        # ADD COLUMN
        add_match = re.search(
            r'ADD\s+(?:COLUMN\s+)?[`"\']?(\w+)[`"\']?\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?)',
            rest,
            re.IGNORECASE
        )
        if add_match:
            col_name = add_match.group(1)
            col_type = add_match.group(2).upper().strip()
            if col_type.count('(') > col_type.count(')'):
                col_type += ')'
            if table_name in self.tables:
                self.tables[table_name].columns[col_name] = col_type
            else:
                self.tables[table_name] = TableSchema(
                    name=table_name,
                    columns={col_name: col_type},
                    indexes=set(),
                    constraints=set()
                )
            logger.debug("ALTER ADD COLUMN %s.%s %s", table_name, col_name, col_type)
            return

        # DROP COLUMN
        drop_match = re.search(
            r'DROP\s+(?:COLUMN\s+)?[`"\']?(\w+)[`"\']?',
            rest,
            re.IGNORECASE
        )
        if drop_match:
            col_name = drop_match.group(1)
            if table_name in self.tables and col_name in self.tables[table_name].columns:
                del self.tables[table_name].columns[col_name]
            logger.debug("ALTER DROP COLUMN %s.%s", table_name, col_name)
            return

        # MODIFY COLUMN / ALTER COLUMN (type change)
        modify_match = re.search(
            r'(?:MODIFY|ALTER)\s+(?:COLUMN\s+)?[`"\']?(\w+)[`"\']?\s+(?:TYPE\s+)?([A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?)',
            rest,
            re.IGNORECASE
        )
        if modify_match:
            col_name = modify_match.group(1)
            new_type = modify_match.group(2).upper().strip()
            if new_type.count('(') > new_type.count(')'):
                new_type += ')'
            if table_name in self.tables:
                self.tables[table_name].columns[col_name] = new_type
            logger.debug("ALTER MODIFY COLUMN %s.%s -> %s", table_name, col_name, new_type)
            return

        # CHANGE COLUMN (MySQL syntax: CHANGE [COLUMN] old_name new_name type)
        change_match = re.search(
            r'CHANGE\s+(?:COLUMN\s+)?[`"\']?(\w+)[`"\']?\s+[`"\']?(\w+)[`"\']?\s+([A-Za-z_][A-Za-z0-9_]*(?:\s*\([^)]*\))?)',
            rest,
            re.IGNORECASE
        )
        if change_match:
            old_col = change_match.group(1)
            new_col = change_match.group(2)
            new_type = change_match.group(3).upper().strip()
            if new_type.count('(') > new_type.count(')'):
                new_type += ')'
            if table_name in self.tables:
                if old_col in self.tables[table_name].columns:
                    del self.tables[table_name].columns[old_col]
                self.tables[table_name].columns[new_col] = new_type
            logger.debug("ALTER CHANGE COLUMN %s.%s -> %s (%s)", table_name, old_col, new_col, new_type)
            return

        logger.debug("ALTER statement not fully parsed: %s", statement_str[:120])

    def _process_drop_statement(self, statement) -> None:
        """处理DROP语句 - 识别 DROP TABLE / DROP INDEX / DROP CONSTRAINT"""
        statement_str = str(statement).strip()

        # DROP TABLE
        drop_table_match = re.search(
            r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?',
            statement_str,
            re.IGNORECASE
        )
        if drop_table_match:
            table_name = drop_table_match.group(1)
            if table_name in self.tables:
                del self.tables[table_name]
            logger.debug("DROP TABLE %s", table_name)
            return

        # DROP INDEX
        drop_index_match = re.search(
            r'DROP\s+INDEX\s+(?:IF\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s+(?:ON\s+[`"\']?(\w+)[`"\']?)?',
            statement_str,
            re.IGNORECASE
        )
        if drop_index_match:
            index_name = drop_index_match.group(1)
            table_name = drop_index_match.group(2)
            if table_name and table_name in self.tables:
                self.tables[table_name].indexes.discard(index_name)
            logger.debug("DROP INDEX %s ON %s", index_name, table_name)
            return

        logger.debug("DROP statement not fully parsed: %s", statement_str[:120])


class SchemaDiff:
    """模式差异分析器"""

    def __init__(self):
        self.parser = SQLParser()

    def compare_schemas(self, base_schema_path: str, target_schema_path: str) -> List[SchemaChange]:
        """比较两个模式文件，返回变更列表"""
        base_tables = self.parser.parse_sql_file(base_schema_path)
        target_tables = self.parser.parse_sql_file(target_schema_path)

        return self._analyze_differences(base_tables, target_tables)

    def compare_schema_content(self, base_content: str, target_content: str) -> List[SchemaChange]:
        """比较两个模式内容，返回变更列表"""
        base_parser = SQLParser()
        target_parser = SQLParser()

        base_tables = base_parser.parse_sql_content(base_content)
        target_tables = target_parser.parse_sql_content(target_content)

        return self._analyze_differences(base_tables, target_tables)

    def _analyze_differences(self, base_tables: Dict[str, TableSchema],
                           target_tables: Dict[str, TableSchema]) -> List[SchemaChange]:
        """分析两个表结构字典的差异"""
        changes = []

        base_table_names = set(base_tables.keys())
        target_table_names = set(target_tables.keys())

        # 检查新增的表
        for table_name in target_table_names - base_table_names:
            changes.append(SchemaChange(
                change_type=ChangeType.TABLE_ADDED,
                table_name=table_name,
                new_name=table_name,
                details={'columns': list(target_tables[table_name].columns.keys())}
            ))

        # 检查删除的表
        for table_name in base_table_names - target_table_names:
            changes.append(SchemaChange(
                change_type=ChangeType.TABLE_DELETED,
                table_name=table_name,
                old_name=table_name,
                details={'columns': list(base_tables[table_name].columns.keys())}
            ))

        # 检查共同存在的表的变更
        common_tables = base_table_names & target_table_names
        for table_name in common_tables:
            base_table = base_tables[table_name]
            target_table = target_tables[table_name]

            table_changes = self._compare_table_structure(base_table, target_table)
            changes.extend(table_changes)

        return changes

    def _compare_table_structure(self, base_table: TableSchema,
                               target_table: TableSchema) -> List[SchemaChange]:
        """比较单个表的结构变更"""
        changes = []
        table_name = base_table.name

        base_columns = set(base_table.columns.keys())
        target_columns = set(target_table.columns.keys())

        # 检查新增的列
        for column_name in target_columns - base_columns:
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                table_name=table_name,
                column_name=column_name,
                new_name=column_name,
                new_type=target_table.columns[column_name],
                details={'table': table_name}
            ))

        # 检查删除的列
        for column_name in base_columns - target_columns:
            changes.append(SchemaChange(
                change_type=ChangeType.COLUMN_DELETED,
                table_name=table_name,
                column_name=column_name,
                old_name=column_name,
                old_type=base_table.columns[column_name],
                details={'table': table_name}
            ))

        # 检查共同存在的列的类型变更
        common_columns = base_columns & target_columns
        for column_name in common_columns:
            base_type = base_table.columns[column_name]
            target_type = target_table.columns[column_name]

            if base_type != target_type:
                changes.append(SchemaChange(
                    change_type=ChangeType.COLUMN_TYPE_CHANGED,
                    table_name=table_name,
                    column_name=column_name,
                    old_type=base_type,
                    new_type=target_type,
                    details={'table': table_name}
                ))

        # 检查索引变更
        base_indexes = base_table.indexes
        target_indexes = target_table.indexes

        for index_name in target_indexes - base_indexes:
            changes.append(SchemaChange(
                change_type=ChangeType.INDEX_ADDED,
                table_name=table_name,
                new_name=index_name,
                details={'table': table_name, 'index': index_name}
            ))

        for index_name in base_indexes - target_indexes:
            changes.append(SchemaChange(
                change_type=ChangeType.INDEX_DELETED,
                table_name=table_name,
                old_name=index_name,
                details={'table': table_name, 'index': index_name}
            ))

        return changes
