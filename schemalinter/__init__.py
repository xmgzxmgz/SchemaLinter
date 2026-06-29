"""
SchemaLinter - 数据库模式变更影响分析工具

这是一个用于分析数据库模式变更对应用代码影响的静态分析工具。
"""

__version__ = "1.0.0"
__author__ = "SchemaLinter Team"
__description__ = "数据库模式变更影响分析工具"

from .core.analyzer import SchemaLinter
from .core.config import Config

__all__ = ["SchemaLinter", "Config"]
