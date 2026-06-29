"""
配置与输入模块

负责处理用户配置、命令行参数和配置文件解析。
"""

import os
import logging
import yaml
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """SchemaLinter 配置类"""

    # 基本配置
    project_path: str = ""
    programming_language: str = "python"
    db_connector_type: str = "raw_sql"  # raw_sql, sqlalchemy, hibernate

    # 数据库模式文件路径
    base_schema_path: str = ""
    target_schema_path: str = ""

    # 数据库连接（可选）
    database_url: Optional[str] = None

    # Git 配置
    git_enabled: bool = False
    base_branch: str = "main"
    target_branch: str = "HEAD"

    # 输出配置
    output_format: str = "console"  # console, json, markdown
    output_file: Optional[str] = None
    verbose: bool = False

    # 代码解析配置
    include_patterns: List[str] = field(default_factory=lambda: ["*.py", "*.java", "*.js", "*.sql"])
    exclude_patterns: List[str] = field(default_factory=lambda: ["**/node_modules/**", "**/venv/**", "**/__pycache__/**"])

    # 分析配置
    strict_mode: bool = False
    ignore_warnings: bool = False
    max_depth: int = 10

    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """从配置文件加载配置"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                data = yaml.safe_load(f)
            elif config_path.endswith('.json'):
                data = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {config_path}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """从字典创建配置对象，支持嵌套配置（如 file_patterns、output）"""
        config = cls()

        for key, value in data.items():
            if key == 'file_patterns' and isinstance(value, dict):
                if 'include' in value:
                    config.include_patterns = value['include']
                if 'exclude' in value:
                    config.exclude_patterns = value['exclude']
            elif key == 'output' and isinstance(value, dict):
                if 'format' in value:
                    config.output_format = value['format']
                if 'file' in value:
                    config.output_file = value['file']
            elif hasattr(config, key):
                setattr(config, key, value)

        return config

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'project_path': self.project_path,
            'programming_language': self.programming_language,
            'db_connector_type': self.db_connector_type,
            'base_schema_path': self.base_schema_path,
            'target_schema_path': self.target_schema_path,
            'database_url': self.database_url,
            'git_enabled': self.git_enabled,
            'base_branch': self.base_branch,
            'target_branch': self.target_branch,
            'output_format': self.output_format,
            'output_file': self.output_file,
            'verbose': self.verbose,
            'include_patterns': self.include_patterns,
            'exclude_patterns': self.exclude_patterns,
            'strict_mode': self.strict_mode,
            'ignore_warnings': self.ignore_warnings,
            'max_depth': self.max_depth,
        }

    def validate(self) -> List[str]:
        """验证配置的有效性，返回错误列表"""
        errors = []

        if not self.project_path:
            errors.append("project_path 不能为空")
        elif not os.path.exists(self.project_path):
            errors.append(f"项目路径不存在: {self.project_path}")

        if not self.git_enabled:
            if not self.target_schema_path:
                errors.append("target_schema_path 不能为空（请至少提供一个 .sql 文件）")
            elif not os.path.exists(self.target_schema_path):
                errors.append(f"目标模式文件不存在: {self.target_schema_path}")

            # base_schema_path is optional for single-file analysis
            if self.base_schema_path and not os.path.exists(self.base_schema_path):
                errors.append(f"基础模式文件不存在: {self.base_schema_path}")

        if self.programming_language not in ['python', 'java', 'javascript', 'typescript']:
            errors.append(f"不支持的编程语言: {self.programming_language}")

        if self.db_connector_type not in ['raw_sql', 'sqlalchemy', 'hibernate', 'jpa', 'sequelize']:
            errors.append(f"不支持的数据库连接器类型: {self.db_connector_type}")

        if self.output_format not in ['console', 'json', 'markdown']:
            errors.append(f"不支持的输出格式: {self.output_format}")

        return errors

    def get_absolute_path(self, path: str) -> str:
        """获取相对于项目路径的绝对路径"""
        if os.path.isabs(path):
            return path
        return os.path.join(self.project_path, path)


def create_default_config() -> Config:
    """创建默认配置"""
    return Config(
        project_path=os.getcwd(),
        programming_language="python",
        db_connector_type="raw_sql",
        output_format="console",
        include_patterns=["*.py", "*.sql"],
        exclude_patterns=["**/venv/**", "**/__pycache__/**", "**/node_modules/**"],
    )
