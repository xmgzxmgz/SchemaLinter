"""
JSON报告生成器

生成JSON格式的结构化报告，适合程序化处理。
"""

import json
from datetime import datetime
from typing import Dict, Any, List

from .base import BaseReporter
from ..core.analyzer import AnalysisReport, ImpactIssue, ImpactLevel
from ..core.schema_diff import SchemaChange, ChangeType
from .. import __version__


class JSONReporter(BaseReporter):
    """JSON报告生成器"""

    def __init__(self, output_file: str = None, indent: int = 2):
        """
        初始化JSON报告生成器

        Args:
            output_file: 输出文件路径
            indent: JSON缩进空格数
        """
        super().__init__(output_file)
        self.indent = indent

    def generate_report(self, report: AnalysisReport) -> str:
        """生成JSON报告"""
        report_data = {
            "metadata": self._generate_metadata(),
            "summary": self._generate_summary(report),
            "changes": self._generate_changes_data(report.changes),
            "issues": self._generate_issues_data(report.issues),
            "statistics": self._generate_statistics(report)
        }

        return json.dumps(report_data, ensure_ascii=False, indent=self.indent)

    def _generate_metadata(self) -> Dict[str, Any]:
        """生成元数据"""
        return {
            "tool": "SchemaLinter",
            "version": __version__,
            "generated_at": datetime.now().isoformat(),
            "format_version": "1.0"
        }

    def _generate_summary(self, report: AnalysisReport) -> Dict[str, Any]:
        """生成摘要数据"""
        return {
            "project_path": report.project_path,
            "total_changes": report.total_changes,
            "total_issues": report.total_issues,
            "critical_issues": report.critical_issues,
            "warning_issues": report.warning_issues,
            "info_issues": report.info_issues,
            "summary_text": report.summary
        }

    def _generate_changes_data(self, changes: List[SchemaChange]) -> List[Dict[str, Any]]:
        """生成变更数据"""
        changes_data = []

        for change in changes:
            change_data = {
                "change_type": change.change_type.value,
                "table_name": change.table_name,
                "old_name": change.old_name,
                "new_name": change.new_name,
                "column_name": change.column_name,
                "old_type": change.old_type,
                "new_type": change.new_type,
                "details": change.details or {}
            }
            changes_data.append(change_data)

        return changes_data

    def _generate_issues_data(self, issues: List[ImpactIssue]) -> List[Dict[str, Any]]:
        """生成问题数据"""
        issues_data = []

        for issue in issues:
            issue_data = {
                "file_path": issue.file_path,
                "line_number": issue.line_number,
                "impact_level": issue.impact_level.value,
                "issue_type": issue.issue_type,
                "description": issue.description,
                "suggestion": issue.suggestion,
                "details": issue.details or {}
            }

            # 添加变更信息
            if issue.change:
                issue_data["related_change"] = {
                    "change_type": issue.change.change_type.value,
                    "table_name": issue.change.table_name,
                    "old_name": issue.change.old_name,
                    "new_name": issue.change.new_name,
                    "column_name": issue.change.column_name
                }

            # 添加代码引用信息
            if issue.reference:
                issue_data["code_reference"] = {
                    "reference_type": issue.reference.reference_type.value,
                    "table_name": issue.reference.table_name,
                    "column_name": issue.reference.column_name,
                    "sql_content": issue.reference.sql_content,
                    "context": issue.reference.context
                }

            issues_data.append(issue_data)

        return issues_data

    def _generate_statistics(self, report: AnalysisReport) -> Dict[str, Any]:
        """生成统计数据"""
        # 按变更类型统计
        change_type_counts = {}
        for change in report.changes:
            change_type = change.change_type.value
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1

        # 按问题类型统计
        issue_type_counts = {}
        for issue in report.issues:
            issue_type = issue.issue_type
            issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1

        # 按文件统计问题
        file_issue_counts = {}
        for issue in report.issues:
            file_path = issue.file_path
            file_issue_counts[file_path] = file_issue_counts.get(file_path, 0) + 1

        # 按影响级别统计
        level_counts = {
            "critical": report.critical_issues,
            "warning": report.warning_issues,
            "info": report.info_issues
        }

        return {
            "change_type_distribution": change_type_counts,
            "issue_type_distribution": issue_type_counts,
            "file_issue_distribution": file_issue_counts,
            "impact_level_distribution": level_counts,
            "most_affected_files": self._get_most_affected_files(file_issue_counts, 5)
        }

    def _get_most_affected_files(self, file_counts: Dict[str, int], limit: int) -> List[Dict[str, Any]]:
        """获取受影响最多的文件"""
        sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {"file_path": file_path, "issue_count": count}
            for file_path, count in sorted_files[:limit]
        ]
