# SchemaLinter

一个强大的数据库模式变更影响分析工具，帮助开发者自动识别数据库结构变化对应用代码的影响。

## 功能特性

- 🔍 **智能变更检测**: 自动识别数据库模式的各种变更类型
- 📝 **多语言代码解析**: 支持 Python、Java 等主流编程语言
- 🔗 **ORM 框架支持**: 支持 SQLAlchemy、Hibernate 等 ORM 框架
- 📊 **多格式报告**: 支持控制台、JSON、Markdown 等多种输出格式
- ⚙️ **灵活配置**: 支持配置文件和命令行参数
- 🎯 **精准分析**: 准确定位受影响的代码文件和行号

## 安装

### 从源码安装

```bash
git clone <repository-url>
cd SchemaLinter
pip install -e .
```

### 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 创建配置文件

```bash
schemalinter init
```

这将创建一个默认的 `schemalinter.yaml` 配置文件。

### 2. 编辑配置文件

```yaml
# 项目基本信息
project_path: "/path/to/your/project"
programming_language: "python"
db_connector_type: "sqlalchemy"

# 数据库模式文件
base_schema_path: "schemas/old_schema.sql"
target_schema_path: "schemas/new_schema.sql"

# 文件匹配模式
file_patterns:
  include:
    - "**/*.py"
    - "**/*.sql"
  exclude:
    - "**/migrations/**"
    - "**/tests/**"

# 输出配置
output:
  format: "console"
  file: null
```

### 3. 运行分析

```bash
# 使用配置文件
schemalinter analyze -c schemalinter.yaml

# 或直接使用命令行参数
schemalinter analyze -p /path/to/project -b old_schema.sql -t new_schema.sql
```

## 使用示例

### 基本分析

```bash
schemalinter analyze \
  --project-path /path/to/my/app \
  --base-schema schemas/v1.sql \
  --target-schema schemas/v2.sql \
  --language python \
  --db-connector sqlalchemy
```

### 生成 JSON 报告

```bash
schemalinter analyze \
  --config schemalinter.yaml \
  --output-format json \
  --output-file report.json
```

### 生成 Markdown 报告

```bash
schemalinter analyze \
  --config schemalinter.yaml \
  --output-format markdown \
  --output-file report.md
```

### 验证配置文件

```bash
schemalinter validate --config schemalinter.yaml
```

## 支持的变更类型

- **表操作**
  - 新增表 (TABLE_ADDED)
  - 删除表 (TABLE_DELETED)
  - 重命名表 (TABLE_RENAMED)

- **列操作**
  - 新增列 (COLUMN_ADDED)
  - 删除列 (COLUMN_DELETED)
  - 重命名列 (COLUMN_RENAMED)
  - 列类型变更 (COLUMN_TYPE_CHANGED)

- **索引操作**
  - 新增索引 (INDEX_ADDED)
  - 删除索引 (INDEX_DELETED)

## 支持的编程语言和框架

### Python
- 原生 SQL 字符串
- SQLAlchemy ORM
- Django ORM (计划支持)

### Java
- JDBC 原生 SQL
- Hibernate ORM (计划支持)
- MyBatis (计划支持)

## 报告格式

### 控制台输出
彩色的控制台输出，包含摘要、变更详情和影响分析。

### JSON 格式
结构化的 JSON 报告，适合程序化处理和 CI/CD 集成。

```json
{
  "metadata": {
    "tool": "SchemaLinter",
    "version": "1.0.0",
    "generated_at": "2024-01-01T12:00:00"
  },
  "summary": {
    "total_changes": 5,
    "total_issues": 3,
    "critical_issues": 1,
    "warning_issues": 2
  },
  "changes": [...],
  "issues": [...],
  "statistics": {...}
}
```

### Markdown 格式
可读性强的 Markdown 报告，适合文档和展示。

## 配置选项

### 项目配置
- `project_path`: 项目根目录
- `programming_language`: 编程语言 (python, java)
- `db_connector_type`: 数据库连接方式 (raw_sql, sqlalchemy, hibernate)

### 模式文件配置
- `base_schema_path`: 基础模式文件路径
- `target_schema_path`: 目标模式文件路径

### 文件匹配配置
- `file_patterns.include`: 包含的文件模式
- `file_patterns.exclude`: 排除的文件模式

### Git 配置 (计划支持)
- `git.enabled`: 是否启用 Git 集成
- `git.base_branch`: 基础分支
- `git.target_branch`: 目标分支

### 输出配置
- `output.format`: 输出格式 (console, json, markdown)
- `output.file`: 输出文件路径

## 退出码

- `0`: 分析完成，无问题
- `1`: 分析完成，发现警告级别问题
- `2`: 分析完成，发现严重问题
- `其他`: 分析过程中出现错误

## 开发指南

### 项目结构

```
schemalinter/
├── core/                 # 核心模块
│   ├── config.py        # 配置管理
│   ├── schema_diff.py   # 模式差异分析
│   └── analyzer.py      # 主分析器
├── parsers/             # 代码解析器
│   ├── base.py         # 基础解析器
│   ├── python_parser.py # Python 解析器
│   └── sql_parser.py   # SQL 解析器
├── reporters/           # 报告生成器
│   ├── base.py         # 基础报告器
│   ├── console_reporter.py # 控制台报告器
│   ├── json_reporter.py    # JSON 报告器
│   └── markdown_reporter.py # Markdown 报告器
└── cli.py              # 命令行接口
```

### 添加新的解析器

1. 继承 `BaseParser` 类
2. 实现 `get_supported_extensions()` 方法
3. 实现 `parse_file()` 方法
4. 在 `__init__.py` 中注册解析器

### 添加新的报告格式

1. 继承 `BaseReporter` 类
2. 实现 `generate_report()` 方法
3. 在 CLI 中添加新的输出格式选项

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 更新日志

### v1.0.0
- 初始版本发布
- 支持 Python 和 SQL 文件解析
- 支持多种输出格式
- 完整的 CLI 工具