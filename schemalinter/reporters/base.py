"""
报告生成器基类

定义报告生成器的基础接口。
"""

from abc import ABC, abstractmethod
from typing import Optional
from ..core.analyzer import AnalysisReport


class BaseReporter(ABC):
    """报告生成器基类"""
    
    def __init__(self, output_file: Optional[str] = None):
        """
        初始化报告生成器
        
        Args:
            output_file: 输出文件路径，如果为None则输出到控制台
        """
        self.output_file = output_file
    
    @abstractmethod
    def generate_report(self, report: AnalysisReport) -> str:
        """
        生成报告内容
        
        Args:
            report: 分析报告对象
            
        Returns:
            报告内容字符串
        """
        pass
    
    def save_report(self, report: AnalysisReport) -> None:
        """
        保存报告到文件或输出到控制台
        
        Args:
            report: 分析报告对象
        """
        content = self.generate_report(report)
        
        if self.output_file:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"报告已保存到: {self.output_file}")
        else:
            print(content)