"""
SchemaLinter 命令行接口

提供易于使用的命令行工具，支持多种分析模式和输出格式。
"""

import os
import sys
import click
from pathlib import Path
from typing import Optional

from .core.config import Config, create_default_config
from .core.analyzer import SchemaLinter
from .reporters import ConsoleReporter, JSONReporter, MarkdownReporter


@click.group()
@click.version_option(version="1.0.0", prog_name="SchemaLinter")
def cli():
    """
    SchemaLinter - 数据库模式变更影响分析工具
    
    自动分析数据库模式变更对应用代码的影响，帮助开发者提前发现潜在问题。
    """
    pass


@cli.command()
@click.option('--project-path', '-p', 
              type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='项目根目录路径')
@click.option('--base-schema', '-b',
              type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help='基础模式文件路径 (旧版本)')
@click.option('--target-schema', '-t',
              type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help='目标模式文件路径 (新版本)')
@click.option('--config', '-c',
              type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help='配置文件路径')
@click.option('--output-format', '-f',
              type=click.Choice(['console', 'json', 'markdown'], case_sensitive=False),
              default='console',
              help='输出格式 (默认: console)')
@click.option('--output-file', '-o',
              type=click.Path(file_okay=True, dir_okay=False),
              help='输出文件路径 (仅适用于 json 和 markdown 格式)')
@click.option('--language', '-l',
              type=click.Choice(['python', 'java'], case_sensitive=False),
              help='项目编程语言')
@click.option('--db-connector',
              type=click.Choice(['raw_sql', 'sqlalchemy', 'hibernate'], case_sensitive=False),
              help='数据库连接方式')
@click.option('--include-patterns',
              multiple=True,
              help='包含的文件模式 (可多次指定)')
@click.option('--exclude-patterns',
              multiple=True,
              help='排除的文件模式 (可多次指定)')
@click.option('--verbose', '-v',
              is_flag=True,
              help='详细输出')
def analyze(project_path: Optional[str],
           base_schema: Optional[str],
           target_schema: Optional[str],
           config: Optional[str],
           output_format: str,
           output_file: Optional[str],
           language: Optional[str],
           db_connector: Optional[str],
           include_patterns: tuple,
           exclude_patterns: tuple,
           verbose: bool):
    """
    分析数据库模式变更对代码的影响
    
    示例:
    
    \b
    # 基本分析
    schemalinter analyze -p /path/to/project -b old_schema.sql -t new_schema.sql
    
    \b
    # 使用配置文件
    schemalinter analyze -c config.yaml
    
    \b
    # 生成 JSON 报告
    schemalinter analyze -p /path/to/project -b old.sql -t new.sql -f json -o report.json
    """
    try:
        # 加载配置
        if config:
            config_obj = Config.from_file(config)
        else:
            # 从命令行参数创建配置
            config_data = {}
            
            if project_path:
                config_data['project_path'] = project_path
            if base_schema:
                config_data['base_schema_path'] = base_schema
            if target_schema:
                config_data['target_schema_path'] = target_schema
            if language:
                config_data['programming_language'] = language
            if db_connector:
                config_data['db_connector_type'] = db_connector
            
            # 文件模式配置
            if include_patterns or exclude_patterns:
                config_data['file_patterns'] = {}
                if include_patterns:
                    config_data['file_patterns']['include'] = list(include_patterns)
                if exclude_patterns:
                    config_data['file_patterns']['exclude'] = list(exclude_patterns)
            
            # 输出配置
            config_data['output'] = {
                'format': output_format,
                'file': output_file
            }
            
            config_obj = Config.from_dict(config_data)
        
        # 验证配置
        config_obj.validate()
        
        if verbose:
            click.echo(f"📁 项目路径: {config_obj.project_path}")
            click.echo(f"📄 基础模式: {config_obj.base_schema_path}")
            click.echo(f"📄 目标模式: {config_obj.target_schema_path}")
            click.echo(f"🔧 编程语言: {config_obj.programming_language}")
            click.echo(f"🔗 数据库连接: {config_obj.db_connector_type}")
            click.echo()
        
        # 创建分析器
        linter = SchemaLinter(config_obj)
        
        # 执行分析
        click.echo("🔍 开始分析...")
        report = linter.analyze()
        
        # 生成报告
        click.echo("📊 生成报告...")
        reporter = _create_reporter(output_format, output_file)
        report_content = reporter.generate_report(report)
        
        # 输出报告
        if output_file and output_format != 'console':
            reporter.save_report(report_content)
            click.echo(f"✅ 报告已保存到: {output_file}")
        else:
            click.echo(report_content)
        
        # 根据问题严重程度设置退出码
        if report.critical_issues > 0:
            sys.exit(2)  # 严重问题
        elif report.warning_issues > 0:
            sys.exit(1)  # 警告问题
        else:
            sys.exit(0)  # 无问题
            
    except Exception as e:
        click.echo(f"❌ 错误: {str(e)}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


@cli.command()
@click.option('--output', '-o',
              type=click.Path(file_okay=True, dir_okay=False),
              default='schemalinter.yaml',
              help='配置文件输出路径 (默认: schemalinter.yaml)')
@click.option('--format', '-f',
              type=click.Choice(['yaml', 'json'], case_sensitive=False),
              default='yaml',
              help='配置文件格式 (默认: yaml)')
def init(output: str, format: str):
    """
    创建默认配置文件
    
    生成一个包含所有可用选项的示例配置文件。
    """
    try:
        config = create_default_config()
        
        if format.lower() == 'json':
            import json
            content = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
        else:
            import yaml
            content = yaml.dump(config.to_dict(), default_flow_style=False, allow_unicode=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        
        click.echo(f"✅ 默认配置文件已创建: {output}")
        click.echo("📝 请根据您的项目需求修改配置文件")
        
    except Exception as e:
        click.echo(f"❌ 创建配置文件失败: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c',
              type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help='配置文件路径')
def validate(config: Optional[str]):
    """
    验证配置文件
    
    检查配置文件的语法和内容是否正确。
    """
    try:
        if not config:
            # 查找默认配置文件
            for filename in ['schemalinter.yaml', 'schemalinter.yml', 'schemalinter.json']:
                if os.path.exists(filename):
                    config = filename
                    break
            
            if not config:
                click.echo("❌ 未找到配置文件，请使用 --config 指定或运行 'schemalinter init' 创建", err=True)
                sys.exit(1)
        
        click.echo(f"🔍 验证配置文件: {config}")
        
        config_obj = Config.from_file(config)
        config_obj.validate()
        
        click.echo("✅ 配置文件验证通过")
        
        # 显示配置摘要
        click.echo("\n📋 配置摘要:")
        click.echo(f"  项目路径: {config_obj.project_path}")
        click.echo(f"  编程语言: {config_obj.programming_language}")
        click.echo(f"  数据库连接: {config_obj.db_connector_type}")
        click.echo(f"  基础模式: {config_obj.base_schema_path}")
        click.echo(f"  目标模式: {config_obj.target_schema_path}")
        
    except Exception as e:
        click.echo(f"❌ 配置文件验证失败: {str(e)}", err=True)
        sys.exit(1)


def _create_reporter(output_format: str, output_file: Optional[str]):
    """创建报告生成器"""
    if output_format == 'json':
        return JSONReporter(output_file)
    elif output_format == 'markdown':
        return MarkdownReporter(output_file)
    else:
        return ConsoleReporter()


if __name__ == '__main__':
    cli()