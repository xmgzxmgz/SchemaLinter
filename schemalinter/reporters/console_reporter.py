"""
控制台报告生成器

生成适合在控制台显示的彩色报告。
"""

from typing import List
from colorama import Fore, Back, Style, init
from tabulate import tabulate

from .base import BaseReporter
from ..core.analyzer import AnalysisReport, ImpactIssue, ImpactLevel

# 初始化colorama
init(autoreset=True)


class ConsoleReporter(BaseReporter):
    """控制台报告生成器"""
    
    def __init__(self, output_file: str = None, verbose: bool = False):
        """
        初始化控制台报告生成器
        
        Args:
            output_file: 输出文件路径
            verbose: 是否显示详细信息
        """
        super().__init__(output_file)
        self.verbose = verbose
        
        # 定义颜色映射
        self.level_colors = {
            ImpactLevel.CRITICAL: Fore.RED,
            ImpactLevel.WARNING: Fore.YELLOW,
            ImpactLevel.INFO: Fore.BLUE,
        }
        
        self.level_symbols = {
            ImpactLevel.CRITICAL: "❌",
            ImpactLevel.WARNING: "⚠️ ",
            ImpactLevel.INFO: "ℹ️ ",
        }
    
    def generate_report(self, report: AnalysisReport) -> str:
        """生成控制台报告"""
        lines = []
        
        # 标题
        lines.append(self._format_title("SchemaLinter 分析报告"))
        lines.append("")
        
        # 摘要
        lines.append(self._format_section_title("📊 分析摘要"))
        lines.append(self._format_summary(report))
        lines.append("")
        
        # 模式变更概览
        if report.changes:
            lines.append(self._format_section_title("🔄 模式变更概览"))
            lines.append(self._format_changes_summary(report))
            lines.append("")
        
        # 问题详情
        if report.issues:
            lines.append(self._format_section_title("🐛 问题详情"))
            lines.append(self._format_issues(report.issues))
            lines.append("")
        
        # 详细信息（如果启用verbose模式）
        if self.verbose and report.changes:
            lines.append(self._format_section_title("📋 详细变更列表"))
            lines.append(self._format_detailed_changes(report))
            lines.append("")
        
        # 建议
        lines.append(self._format_section_title("💡 建议"))
        lines.append(self._format_recommendations(report))
        
        return "\n".join(lines)
    
    def _format_title(self, title: str) -> str:
        """格式化标题"""
        border = "=" * len(title)
        return f"{Fore.CYAN}{Style.BRIGHT}{border}\n{title}\n{border}{Style.RESET_ALL}"
    
    def _format_section_title(self, title: str) -> str:
        """格式化章节标题"""
        return f"{Fore.GREEN}{Style.BRIGHT}{title}{Style.RESET_ALL}"
    
    def _format_summary(self, report: AnalysisReport) -> str:
        """格式化摘要信息"""
        lines = []
        
        # 基本统计
        lines.append(f"项目路径: {report.project_path}")
        lines.append(f"模式变更: {report.total_changes} 个")
        lines.append(f"影响问题: {report.total_issues} 个")
        
        if report.total_issues > 0:
            lines.append("")
            lines.append("问题分布:")
            if report.critical_issues > 0:
                lines.append(f"  {self.level_symbols[ImpactLevel.CRITICAL]} 严重问题: {Fore.RED}{report.critical_issues}{Style.RESET_ALL}")
            if report.warning_issues > 0:
                lines.append(f"  {self.level_symbols[ImpactLevel.WARNING]} 警告问题: {Fore.YELLOW}{report.warning_issues}{Style.RESET_ALL}")
            if report.info_issues > 0:
                lines.append(f"  {self.level_symbols[ImpactLevel.INFO]} 信息提示: {Fore.BLUE}{report.info_issues}{Style.RESET_ALL}")
        
        lines.append("")
        lines.append(f"总结: {report.summary}")
        
        return "\n".join(lines)
    
    def _format_changes_summary(self, report: AnalysisReport) -> str:
        """格式化变更摘要"""
        change_counts = {}
        for change in report.changes:
            change_type = change.change_type.value
            change_counts[change_type] = change_counts.get(change_type, 0) + 1
        
        if not change_counts:
            return "无模式变更"
        
        lines = []
        for change_type, count in sorted(change_counts.items()):
            lines.append(f"  • {change_type.replace('_', ' ').title()}: {count} 个")
        
        return "\n".join(lines)
    
    def _format_issues(self, issues: List[ImpactIssue]) -> str:
        """格式化问题列表"""
        if not issues:
            return f"{Fore.GREEN}✅ 没有发现问题！{Style.RESET_ALL}"
        
        # 按影响级别分组
        grouped_issues = {
            ImpactLevel.CRITICAL: [],
            ImpactLevel.WARNING: [],
            ImpactLevel.INFO: []
        }
        
        for issue in issues:
            grouped_issues[issue.impact_level].append(issue)
        
        lines = []
        
        for level in [ImpactLevel.CRITICAL, ImpactLevel.WARNING, ImpactLevel.INFO]:
            level_issues = grouped_issues[level]
            if not level_issues:
                continue
            
            level_name = level.value.upper()
            color = self.level_colors[level]
            symbol = self.level_symbols[level]
            
            lines.append(f"\n{color}{Style.BRIGHT}{symbol} {level_name} ({len(level_issues)} 个):{Style.RESET_ALL}")
            
            for i, issue in enumerate(level_issues, 1):
                lines.append(self._format_single_issue(issue, i, color))
        
        return "\n".join(lines)
    
    def _format_single_issue(self, issue: ImpactIssue, index: int, color: str) -> str:
        """格式化单个问题"""
        lines = []
        
        # 问题标题
        file_name = issue.file_path.split('/')[-1]
        lines.append(f"\n{color}{index}. {file_name}:{issue.line_number}{Style.RESET_ALL}")
        
        # 问题描述
        lines.append(f"   描述: {issue.description}")
        
        # 建议
        if issue.suggestion:
            lines.append(f"   建议: {Fore.GREEN}{issue.suggestion}{Style.RESET_ALL}")
        
        # 详细信息（verbose模式）
        if self.verbose and issue.reference and issue.reference.context:
            lines.append(f"   上下文:")
            context_lines = issue.reference.context.split('\n')
            for context_line in context_lines:
                lines.append(f"     {Fore.LIGHTBLACK_EX}{context_line}{Style.RESET_ALL}")
        
        return "\n".join(lines)
    
    def _format_detailed_changes(self, report: AnalysisReport) -> str:
        """格式化详细变更列表"""
        if not report.changes:
            return "无变更"
        
        # 准备表格数据
        table_data = []
        for change in report.changes:
            row = [
                change.change_type.value.replace('_', ' ').title(),
                change.table_name or '-',
                change.old_name or '-',
                change.new_name or '-',
                change.column_name or '-',
                f"{change.old_type} → {change.new_type}" if change.old_type and change.new_type else '-'
            ]
            table_data.append(row)
        
        headers = ['变更类型', '表名', '旧名称', '新名称', '列名', '类型变更']
        
        return tabulate(table_data, headers=headers, tablefmt='grid')
    
    def _format_recommendations(self, report: AnalysisReport) -> str:
        """格式化建议"""
        lines = []
        
        if report.critical_issues > 0:
            lines.append(f"{Fore.RED}🚨 立即处理严重问题以避免运行时错误{Style.RESET_ALL}")
        
        if report.warning_issues > 0:
            lines.append(f"{Fore.YELLOW}⚠️  检查警告问题以确保代码兼容性{Style.RESET_ALL}")
        
        if report.total_issues == 0:
            lines.append(f"{Fore.GREEN}🎉 恭喜！您的代码与新的数据库模式完全兼容{Style.RESET_ALL}")
        else:
            lines.append("📝 建议在部署前解决所有发现的问题")
            lines.append("🧪 在测试环境中验证修复后的代码")
        
        if not lines:
            lines.append("暂无特殊建议")
        
        return "\n".join(lines)