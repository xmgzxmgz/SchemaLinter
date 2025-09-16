"""
Markdown报告生成器

生成Markdown格式的可读性强的报告，适合文档和展示。
"""

from datetime import datetime
from typing import List, Dict, Any

from .base import BaseReporter
from ..core.analyzer import AnalysisReport, ImpactIssue, ImpactLevel
from ..core.schema_diff import SchemaChange, ChangeType


class MarkdownReporter(BaseReporter):
    """Markdown报告生成器"""
    
    def __init__(self, output_file: str = None, include_toc: bool = True):
        """
        初始化Markdown报告生成器
        
        Args:
            output_file: 输出文件路径
            include_toc: 是否包含目录
        """
        super().__init__(output_file)
        self.include_toc = include_toc
    
    def generate_report(self, report: AnalysisReport) -> str:
        """生成Markdown报告"""
        sections = []
        
        # 标题和元数据
        sections.append(self._generate_header())
        
        # 目录
        if self.include_toc:
            sections.append(self._generate_toc())
        
        # 摘要
        sections.append(self._generate_summary(report))
        
        # 变更详情
        if report.changes:
            sections.append(self._generate_changes_section(report.changes))
        
        # 影响分析
        if report.issues:
            sections.append(self._generate_issues_section(report.issues))
        
        # 统计信息
        sections.append(self._generate_statistics_section(report))
        
        # 建议
        sections.append(self._generate_recommendations(report))
        
        return "\n\n".join(sections)
    
    def _generate_header(self) -> str:
        """生成报告头部"""
        return f"""# SchemaLinter 分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**工具版本**: SchemaLinter v1.0.0"""
    
    def _generate_toc(self) -> str:
        """生成目录"""
        return """## 目录

- [摘要](#摘要)
- [数据库变更详情](#数据库变更详情)
- [影响分析](#影响分析)
- [统计信息](#统计信息)
- [建议](#建议)"""
    
    def _generate_summary(self, report: AnalysisReport) -> str:
        """生成摘要部分"""
        summary = f"""## 摘要

**项目路径**: `{report.project_path}`

### 分析结果概览

| 指标 | 数量 |
|------|------|
| 数据库变更总数 | {report.total_changes} |
| 发现问题总数 | {report.total_issues} |
| 🔴 严重问题 | {report.critical_issues} |
| 🟡 警告问题 | {report.warning_issues} |
| 🔵 信息提示 | {report.info_issues} |

### 总结

{report.summary}"""
        
        return summary
    
    def _generate_changes_section(self, changes: List[SchemaChange]) -> str:
        """生成变更详情部分"""
        section = "## 数据库变更详情\n\n"
        
        # 按变更类型分组
        changes_by_type = {}
        for change in changes:
            change_type = change.change_type
            if change_type not in changes_by_type:
                changes_by_type[change_type] = []
            changes_by_type[change_type].append(change)
        
        for change_type, type_changes in changes_by_type.items():
            section += f"### {self._get_change_type_title(change_type)}\n\n"
            
            for change in type_changes:
                section += f"- **表**: `{change.table_name}`\n"
                
                if change.old_name and change.new_name:
                    section += f"  - 从 `{change.old_name}` 重命名为 `{change.new_name}`\n"
                elif change.column_name:
                    section += f"  - 列: `{change.column_name}`\n"
                    if change.old_type and change.new_type:
                        section += f"  - 类型变更: `{change.old_type}` → `{change.new_type}`\n"
                
                if change.details:
                    section += f"  - 详情: {change.details}\n"
                
                section += "\n"
        
        return section
    
    def _generate_issues_section(self, issues: List[ImpactIssue]) -> str:
        """生成影响分析部分"""
        section = "## 影响分析\n\n"
        
        # 按影响级别分组
        issues_by_level = {
            ImpactLevel.CRITICAL: [],
            ImpactLevel.WARNING: [],
            ImpactLevel.INFO: []
        }
        
        for issue in issues:
            issues_by_level[issue.impact_level].append(issue)
        
        for level in [ImpactLevel.CRITICAL, ImpactLevel.WARNING, ImpactLevel.INFO]:
            level_issues = issues_by_level[level]
            if not level_issues:
                continue
            
            section += f"### {self._get_impact_level_title(level)}\n\n"
            
            for issue in level_issues:
                section += f"#### {issue.issue_type}\n\n"
                section += f"**文件**: `{issue.file_path}`"
                if issue.line_number:
                    section += f" (第 {issue.line_number} 行)"
                section += "\n\n"
                
                section += f"**问题描述**: {issue.description}\n\n"
                
                if issue.suggestion:
                    section += f"**修改建议**: {issue.suggestion}\n\n"
                
                if issue.reference and issue.reference.sql_content:
                    section += f"**相关代码**:\n```sql\n{issue.reference.sql_content}\n```\n\n"
                
                section += "---\n\n"
        
        return section
    
    def _generate_statistics_section(self, report: AnalysisReport) -> str:
        """生成统计信息部分"""
        section = "## 统计信息\n\n"
        
        # 变更类型分布
        change_type_counts = {}
        for change in report.changes:
            change_type = change.change_type.value
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
        
        if change_type_counts:
            section += "### 变更类型分布\n\n"
            section += "| 变更类型 | 数量 |\n|----------|------|\n"
            for change_type, count in sorted(change_type_counts.items()):
                section += f"| {change_type} | {count} |\n"
            section += "\n"
        
        # 问题类型分布
        issue_type_counts = {}
        for issue in report.issues:
            issue_type = issue.issue_type
            issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1
        
        if issue_type_counts:
            section += "### 问题类型分布\n\n"
            section += "| 问题类型 | 数量 |\n|----------|------|\n"
            for issue_type, count in sorted(issue_type_counts.items()):
                section += f"| {issue_type} | {count} |\n"
            section += "\n"
        
        # 受影响文件
        file_issue_counts = {}
        for issue in report.issues:
            file_path = issue.file_path
            file_issue_counts[file_path] = file_issue_counts.get(file_path, 0) + 1
        
        if file_issue_counts:
            section += "### 受影响最多的文件 (Top 10)\n\n"
            section += "| 文件路径 | 问题数量 |\n|----------|----------|\n"
            sorted_files = sorted(file_issue_counts.items(), key=lambda x: x[1], reverse=True)
            for file_path, count in sorted_files[:10]:
                section += f"| `{file_path}` | {count} |\n"
            section += "\n"
        
        return section
    
    def _generate_recommendations(self, report: AnalysisReport) -> str:
        """生成建议部分"""
        section = "## 建议\n\n"
        
        if report.critical_issues > 0:
            section += "### 🔴 紧急处理\n\n"
            section += "发现了严重问题，建议立即处理以避免运行时错误：\n\n"
            
            critical_issues = [issue for issue in report.issues if issue.impact_level == ImpactLevel.CRITICAL]
            for issue in critical_issues[:5]:  # 只显示前5个
                section += f"- **{issue.file_path}**: {issue.description}\n"
            
            if len(critical_issues) > 5:
                section += f"- ... 还有 {len(critical_issues) - 5} 个严重问题\n"
            section += "\n"
        
        if report.warning_issues > 0:
            section += "### 🟡 建议优化\n\n"
            section += "发现了一些警告问题，建议在下次迭代中处理：\n\n"
            section += "- 检查所有警告级别的问题\n"
            section += "- 更新相关的代码和文档\n"
            section += "- 考虑添加数据迁移脚本\n\n"
        
        section += "### 📋 最佳实践\n\n"
        section += "- 在部署前运行完整的测试套件\n"
        section += "- 准备数据库迁移脚本\n"
        section += "- 更新API文档和数据库文档\n"
        section += "- 考虑向后兼容性\n"
        
        return section
    
    def _get_change_type_title(self, change_type: ChangeType) -> str:
        """获取变更类型的中文标题"""
        titles = {
            ChangeType.TABLE_ADDED: "📋 新增表",
            ChangeType.TABLE_DELETED: "🗑️ 删除表",
            ChangeType.TABLE_RENAMED: "📝 重命名表",
            ChangeType.COLUMN_ADDED: "➕ 新增列",
            ChangeType.COLUMN_DELETED: "➖ 删除列",
            ChangeType.COLUMN_RENAMED: "📝 重命名列",
            ChangeType.COLUMN_TYPE_CHANGED: "🔄 列类型变更",
            ChangeType.INDEX_ADDED: "🔍 新增索引",
            ChangeType.INDEX_DELETED: "🗑️ 删除索引"
        }
        return titles.get(change_type, change_type.value)
    
    def _get_impact_level_title(self, level: ImpactLevel) -> str:
        """获取影响级别的中文标题"""
        titles = {
            ImpactLevel.CRITICAL: "🔴 严重问题",
            ImpactLevel.WARNING: "🟡 警告问题",
            ImpactLevel.INFO: "🔵 信息提示"
        }
        return titles.get(level, level.value)