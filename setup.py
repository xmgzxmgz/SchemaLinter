from setuptools import setup, find_packages

setup(
    name="schemalinter",
    version="1.0.0",
    description="数据库模式变更影响分析工具",
    author="SchemaLinter Team",
    packages=find_packages(),
    install_requires=[
        "sqlparse>=0.4.4",
        "pyyaml>=6.0.1",
        "click>=8.1.7",
        "gitpython>=3.1.40",
        "colorama>=0.4.6",
        "tabulate>=0.9.0",
        "jinja2>=3.1.2",
    ],
    entry_points={
        "console_scripts": [
            "schemalinter=schemalinter.cli:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)