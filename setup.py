from setuptools import setup, find_packages
from pathlib import Path

# Read version from package __init__
init_file = Path(__file__).parent / "schemalinter" / "__init__.py"
version = "1.0.0"
for line in init_file.read_text().splitlines():
    if line.startswith("__version__"):
        version = line.split("=")[1].strip().strip('"').strip("'")
        break

# Read README
try:
    long_description = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")
except FileNotFoundError:
    long_description = ""

setup(
    name="schemalinter",
    version=version,
    description="数据库模式变更影响分析工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="SchemaLinter Team",
    url="https://github.com/xmgzxmgz/SchemaLinter",
    packages=find_packages(),
    install_requires=[
        "sqlparse>=0.4.4",
        "pyyaml>=6.0",
        "click>=8.1",
        "colorama>=0.4.6",
        "tabulate>=0.9.0",
    ],
    extras_require={
        "git": ["gitpython>=3.1"],
        "templates": ["jinja2>=3.1"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "schemalinter=schemalinter.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="database schema lint analysis migration",
)
