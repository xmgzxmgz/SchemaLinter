"""
基础解析器类

定义代码解析器的基础接口和数据结构。
"""

import os
import fnmatch
from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ReferenceType(Enum):
    """代码引用类型"""
    TABLE_REFERENCE = "table_reference"
    COLUMN_REFERENCE = "column_reference"
    SQL_QUERY = "sql_query"
    ORM_MODEL = "orm_model"
    ORM_FIELD = "orm_field"


@dataclass
class CodeReference:
    """代码引用记录"""
    file_path: str
    line_number: int
    reference_type: ReferenceType
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    sql_content: Optional[str] = None
    context: Optional[str] = None  # 上下文代码
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


class BaseParser(ABC):
    """代码解析器基类"""
    
    def __init__(self, project_path: str, include_patterns: List[str] = None, 
                 exclude_patterns: List[str] = None):
        """
        初始化解析器
        
        Args:
            project_path: 项目根目录路径
            include_patterns: 包含的文件模式列表
            exclude_patterns: 排除的文件模式列表
        """
        self.project_path = project_path
        self.include_patterns = include_patterns or ["*"]
        self.exclude_patterns = exclude_patterns or []
        self.references: List[CodeReference] = []
    
    @abstractmethod
    def parse_file(self, file_path: str) -> List[CodeReference]:
        """
        解析单个文件，提取数据库相关的代码引用
        
        Args:
            file_path: 文件路径
            
        Returns:
            代码引用列表
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名列表
        
        Returns:
            文件扩展名列表
        """
        pass
    
    def parse_project(self) -> List[CodeReference]:
        """
        解析整个项目，提取所有数据库相关的代码引用
        
        Returns:
            所有代码引用的列表
        """
        self.references = []
        
        # 获取所有需要解析的文件
        files_to_parse = self._get_files_to_parse()
        
        # 解析每个文件
        for file_path in files_to_parse:
            try:
                file_references = self.parse_file(file_path)
                self.references.extend(file_references)
            except Exception as e:
                print(f"警告: 解析文件 {file_path} 时出错: {e}")
        
        return self.references
    
    def _get_files_to_parse(self) -> List[str]:
        """获取需要解析的文件列表"""
        files = []
        supported_extensions = self.get_supported_extensions()
        
        for root, dirs, filenames in os.walk(self.project_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if not self._should_exclude_dir(os.path.join(root, d))]
            
            for filename in filenames:
                file_path = os.path.join(root, filename)
                
                # 检查文件扩展名
                if not any(filename.endswith(ext) for ext in supported_extensions):
                    continue
                
                # 检查包含模式
                if not self._matches_include_patterns(file_path):
                    continue
                
                # 检查排除模式
                if self._matches_exclude_patterns(file_path):
                    continue
                
                files.append(file_path)
        
        return files
    
    def _should_exclude_dir(self, dir_path: str) -> bool:
        """检查目录是否应该被排除"""
        relative_path = os.path.relpath(dir_path, self.project_path)
        
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(dir_path, pattern):
                return True
        
        return False
    
    def _matches_include_patterns(self, file_path: str) -> bool:
        """检查文件是否匹配包含模式"""
        if not self.include_patterns or self.include_patterns == ["*"]:
            return True
        
        relative_path = os.path.relpath(file_path, self.project_path)
        filename = os.path.basename(file_path)
        
        for pattern in self.include_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True
        
        return False
    
    def _matches_exclude_patterns(self, file_path: str) -> bool:
        """检查文件是否匹配排除模式"""
        if not self.exclude_patterns:
            return False
        
        relative_path = os.path.relpath(file_path, self.project_path)
        filename = os.path.basename(file_path)
        
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(relative_path, pattern):
                return True
        
        return False
    
    def get_references_by_table(self, table_name: str) -> List[CodeReference]:
        """获取引用特定表的代码引用"""
        return [ref for ref in self.references if ref.table_name == table_name]
    
    def get_references_by_column(self, table_name: str, column_name: str) -> List[CodeReference]:
        """获取引用特定列的代码引用"""
        return [ref for ref in self.references 
                if ref.table_name == table_name and ref.column_name == column_name]
    
    def get_references_by_type(self, reference_type: ReferenceType) -> List[CodeReference]:
        """获取特定类型的代码引用"""
        return [ref for ref in self.references if ref.reference_type == reference_type]
    
    def get_all_referenced_tables(self) -> Set[str]:
        """获取所有被引用的表名"""
        return {ref.table_name for ref in self.references if ref.table_name}
    
    def get_all_referenced_columns(self) -> Set[str]:
        """获取所有被引用的列名"""
        return {ref.column_name for ref in self.references if ref.column_name}
    
    def _read_file_content(self, file_path: str) -> str:
        """读取文件内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    return f.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
    
    def _get_line_context(self, content: str, line_number: int, context_lines: int = 2) -> str:
        """获取指定行的上下文"""
        lines = content.split('\n')
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        
        context_lines_list = []
        for i in range(start, end):
            prefix = ">>> " if i == line_number - 1 else "    "
            context_lines_list.append(f"{prefix}{i + 1:4d}: {lines[i]}")
        
        return '\n'.join(context_lines_list)