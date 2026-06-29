"""
影响分析与报告模块

结合模式变更和代码引用，分析影响并生成报告。
"""

import os
import logging
from typing import List, Dict, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .config import Config
from .schema_diff import SchemaDiff, SchemaChange, ChangeType
from ..parsers.base import BaseParser, CodeReference, ReferenceType
from ..parsers.python_parser import PythonParser
from ..parsers.sql_parser import SQLStringParser

logger = logging.getLogger(__name__)


class ImpactLevel(Enum):
    """影响级别"""
    CRITICAL = "critical"  # 严重错误，会导致运行时异常
    WARNING = "warning"    # 警告，可能导致问题
    INFO = "info"         # 信息，需要注意但不会导致错误


@dataclass
class ImpactIssue:
    """影响问题记录"""
    file_path: str
    line_number: int
    impact_level: ImpactLevel
    issue_type: str
    description: str
    suggestion: Optional[str] = None
    change: Optional[SchemaChange] = None
    reference: Optional[CodeReference] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def dedup_key(self) -> tuple:
        """返回用于去重的唯一键"""
        return (self.file_path, self.line_number, self.issue_type,
                self.details.get('table_name', self.details.get('deleted_table', '')))


@dataclass
class AnalysisReport:
    """分析报告"""
    project_path: str
    total_changes: int
    total_issues: int
    critical_issues: int
    warning_issues: int
    info_issues: int
    issues: List[ImpactIssue]
    changes: List[SchemaChange]
    summary: str

    def get_issues_by_level(self, level: ImpactLevel) -> List[ImpactIssue]:
        """获取指定级别的问题"""
        return [issue for issue in self.issues if issue.impact_level == level]

    def get_issues_by_file(self, file_path: str) -> List[ImpactIssue]:
        """获取指定文件的问题"""
        return [issue for issue in self.issues if issue.file_path == file_path]


class SchemaLinter:
    """SchemaLinter主分析器"""

    def __init__(self, config: Config):
        """
        初始化分析器

        Args:
            config: 配置对象
        """
        self.config = config
        self.schema_diff = SchemaDiff()
        self.code_parser: Optional[BaseParser] = None

        # 初始化代码解析器
        self._init_code_parser()

    def _init_code_parser(self) -> None:
        """初始化代码解析器"""
        if self.config.programming_language == "python":
            self.code_parser = PythonParser(
                project_path=self.config.project_path,
                include_patterns=self.config.include_patterns,
                exclude_patterns=self.config.exclude_patterns,
                db_connector_type=self.config.db_connector_type
            )
        else:
            # 默认使用SQL解析器
            self.code_parser = SQLStringParser(
                project_path=self.config.project_path,
                include_patterns=self.config.include_patterns,
                exclude_patterns=self.config.exclude_patterns
            )

    def analyze(self) -> AnalysisReport:
        """
        执行完整的影响分析

        Returns:
            分析报告
        """
        # 1. 识别模式变更
        changes = self._get_schema_changes()

        # 2. 解析代码引用
        references = self._parse_code_references()

        # 3. 分析影响
        issues = self._analyze_impact(changes, references)

        # 4. 去重
        issues = self._deduplicate_issues(issues)

        # 5. 生成报告
        report = self._generate_report(changes, issues)

        return report

    def _get_schema_changes(self) -> List[SchemaChange]:
        """获取模式变更列表"""
        if self.config.git_enabled:
            # TODO: 实现Git集成
            raise NotImplementedError("Git集成功能尚未实现")
        else:
            return self.schema_diff.compare_schemas(
                self.config.base_schema_path,
                self.config.target_schema_path
            )

    def _parse_code_references(self) -> List[CodeReference]:
        """解析代码引用"""
        if self.code_parser is None:
            return []

        return self.code_parser.parse_project()

    def _analyze_impact(self, changes: List[SchemaChange],
                       references: List[CodeReference]) -> List[ImpactIssue]:
        """分析模式变更对代码的影响"""
        issues = []

        for change in changes:
            change_issues = self._analyze_single_change(change, references)
            issues.extend(change_issues)

        return issues

    @staticmethod
    def _deduplicate_issues(issues: List[ImpactIssue]) -> List[ImpactIssue]:
        """根据 (file_path, line_number, issue_type, table_name) 去重"""
        seen = set()
        unique = []
        for issue in issues:
            key = issue.dedup_key()
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        return unique

    def _analyze_single_change(self, change: SchemaChange,
                              references: List[CodeReference]) -> List[ImpactIssue]:
        """分析单个变更的影响"""
        issues = []

        if change.change_type == ChangeType.TABLE_DELETED:
            issues.extend(self._analyze_table_deletion(change, references))
        elif change.change_type == ChangeType.TABLE_RENAMED:
            issues.extend(self._analyze_table_rename(change, references))
        elif change.change_type == ChangeType.COLUMN_DELETED:
            issues.extend(self._analyze_column_deletion(change, references))
        elif change.change_type == ChangeType.COLUMN_RENAMED:
            issues.extend(self._analyze_column_rename(change, references))
        elif change.change_type == ChangeType.COLUMN_TYPE_CHANGED:
            issues.extend(self._analyze_column_type_change(change, references))
        elif change.change_type == ChangeType.TABLE_ADDED:
            issues.extend(self._analyze_table_addition(change, references))
        elif change.change_type == ChangeType.COLUMN_ADDED:
            issues.extend(self._analyze_column_addition(change, references))

        return issues

    def _analyze_table_deletion(self, change: SchemaChange,
                               references: List[CodeReference]) -> List[ImpactIssue]:
        """分析表删除的影响"""
        issues = []

        # 查找所有引用了被删除表的代码
        for ref in references:
            if ref.table_name == change.table_name:
                issues.append(ImpactIssue(
                    file_path=ref.file_path,
                    line_number=ref.line_number,
                    impact_level=ImpactLevel.CRITICAL,
                    issue_type="table_not_found",
                    description=f"表 '{change.table_name}' 已被删除，但仍在代码中被引用",
                    suggestion=f"请移除对表 '{change.table_name}' 的引用或使用替代表",
                    change=change,
                    reference=ref,
                    details={
                        'deleted_table': change.table_name,
                        'table_name': change.table_name,
                        'reference_type': ref.reference_type.value
                    }
                ))

        return issues

    def _analyze_table_rename(self, change: SchemaChange,
                             references: List[CodeReference]) -> List[ImpactIssue]:
        """分析表重命名的影响"""
        issues = []

        # 查找所有引用了旧表名的代码
        for ref in references:
            if ref.table_name == change.old_name:
                issues.append(ImpactIssue(
                    file_path=ref.file_path,
                    line_number=ref.line_number,
                    impact_level=ImpactLevel.CRITICAL,
                    issue_type="table_renamed",
                    description=f"表 '{change.old_name}' 已重命名为 '{change.new_name}'，但代码中仍使用旧名称",
                    suggestion=f"请将表名 '{change.old_name}' 更新为 '{change.new_name}'",
                    change=change,
                    reference=ref,
                    details={
                        'old_table_name': change.old_name,
                        'new_table_name': change.new_name,
                        'table_name': change.old_name,
                        'reference_type': ref.reference_type.value
                    }
                ))

        return issues

    def _analyze_column_deletion(self, change: SchemaChange,
                                references: List[CodeReference]) -> List[ImpactIssue]:
        """分析列删除的影响"""
        issues = []

        # 查找所有引用了被删除列的代码
        for ref in references:
            if (ref.table_name == change.table_name and
                ref.column_name == change.column_name):
                issues.append(ImpactIssue(
                    file_path=ref.file_path,
                    line_number=ref.line_number,
                    impact_level=ImpactLevel.CRITICAL,
                    issue_type="column_not_found",
                    description=f"列 '{change.table_name}.{change.column_name}' 已被删除，但仍在代码中被引用",
                    suggestion=f"请移除对列 '{change.column_name}' 的引用或使用替代列",
                    change=change,
                    reference=ref,
                    details={
                        'table_name': change.table_name,
                        'deleted_column': change.column_name,
                        'reference_type': ref.reference_type.value
                    }
                ))

        return issues

    def _analyze_column_rename(self, change: SchemaChange,
                              references: List[CodeReference]) -> List[ImpactIssue]:
        """分析列重命名的影响"""
        issues = []

        # 查找所有引用了旧列名的代码
        for ref in references:
            if (ref.table_name == change.table_name and
                ref.column_name == change.old_name):
                issues.append(ImpactIssue(
                    file_path=ref.file_path,
                    line_number=ref.line_number,
                    impact_level=ImpactLevel.CRITICAL,
                    issue_type="column_renamed",
                    description=f"列 '{change.table_name}.{change.old_name}' 已重命名为 '{change.new_name}'，但代码中仍使用旧名称",
                    suggestion=f"请将列名 '{change.old_name}' 更新为 '{change.new_name}'",
                    change=change,
                    reference=ref,
                    details={
                        'table_name': change.table_name,
                        'old_column_name': change.old_name,
                        'new_column_name': change.new_name,
                        'reference_type': ref.reference_type.value
                    }
                ))

        return issues

    def _analyze_column_type_change(self, change: SchemaChange,
                                   references: List[CodeReference]) -> List[ImpactIssue]:
        """分析列类型变更的影响"""
        issues = []

        # 查找所有引用了该列的代码
        for ref in references:
            if (ref.table_name == change.table_name and
                ref.column_name == change.column_name):

                # 判断类型变更的严重程度
                impact_level = self._assess_type_change_impact(change.old_type, change.new_type)

                issues.append(ImpactIssue(
                    file_path=ref.file_path,
                    line_number=ref.line_number,
                    impact_level=impact_level,
                    issue_type="column_type_changed",
                    description=f"列 '{change.table_name}.{change.column_name}' 的类型从 '{change.old_type}' 变更为 '{change.new_type}'",
                    suggestion=self._get_type_change_suggestion(change.old_type, change.new_type),
                    change=change,
                    reference=ref,
                    details={
                        'table_name': change.table_name,
                        'column_name': change.column_name,
                        'old_type': change.old_type,
                        'new_type': change.new_type,
                        'reference_type': ref.reference_type.value
                    }
                ))

        return issues

    def _analyze_table_addition(self, change: SchemaChange,
                               references: List[CodeReference]) -> List[ImpactIssue]:
        """分析表添加的影响（通常不会产生问题）"""
        return []

    def _analyze_column_addition(self, change: SchemaChange,
                                references: List[CodeReference]) -> List[ImpactIssue]:
        """分析列添加的影响（通常不会产生问题）"""
        return []

    def _assess_type_change_impact(self, old_type: str, new_type: str) -> ImpactLevel:
        """评估类型变更的影响级别"""
        old_type = old_type.upper()
        new_type = new_type.upper()

        # 简化的类型兼容性检查
        if old_type == new_type:
            return ImpactLevel.INFO

        # 数值类型扩展通常是安全的
        if (old_type in ['INT', 'INTEGER'] and new_type in ['BIGINT', 'LONG']) or \
           (old_type in ['FLOAT'] and new_type in ['DOUBLE']):
            return ImpactLevel.INFO

        # 字符串长度增加通常是安全的
        if 'VARCHAR' in old_type and 'VARCHAR' in new_type:
            return ImpactLevel.WARNING

        # 其他类型变更可能有风险
        return ImpactLevel.WARNING

    def _get_type_change_suggestion(self, old_type: str, new_type: str) -> str:
        """获取类型变更的建议"""
        return f"请检查代码中对该列的使用是否与新类型 '{new_type}' 兼容"

    def _generate_report(self, changes: List[SchemaChange],
                        issues: List[ImpactIssue]) -> AnalysisReport:
        """生成分析报告"""
        critical_count = len([i for i in issues if i.impact_level == ImpactLevel.CRITICAL])
        warning_count = len([i for i in issues if i.impact_level == ImpactLevel.WARNING])
        info_count = len([i for i in issues if i.impact_level == ImpactLevel.INFO])

        # 生成摘要
        summary = self._generate_summary(len(changes), len(issues), critical_count, warning_count, info_count)

        return AnalysisReport(
            project_path=self.config.project_path,
            total_changes=len(changes),
            total_issues=len(issues),
            critical_issues=critical_count,
            warning_issues=warning_count,
            info_issues=info_count,
            issues=issues,
            changes=changes,
            summary=summary
        )

    def _generate_summary(self, total_changes: int, total_issues: int,
                         critical: int, warning: int, info: int) -> str:
        """生成分析摘要"""
        summary_parts = [
            f"检测到 {total_changes} 个数据库模式变更",
            f"发现 {total_issues} 个潜在影响问题"
        ]

        if critical > 0:
            summary_parts.append(f"其中 {critical} 个严重问题需要立即处理")
        if warning > 0:
            summary_parts.append(f"{warning} 个警告问题需要注意")
        if info > 0:
            summary_parts.append(f"{info} 个信息提示")

        if total_issues == 0:
            summary_parts.append("恭喜！没有发现兼容性问题")

        return "，".join(summary_parts) + "。"
