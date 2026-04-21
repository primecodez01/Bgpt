from setuptools import setup, find_packages
import os

# Read README for long description
def read_readme():
    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, "r", encoding="utf-8") as fh:
            return fh.read()
    return "Advanced AI Shell Command Assistant"

# Define requirements directly instead of reading from file
def get_requirements():
    return [
        "rich>=13.7.0",
        "click>=8.1.0",
        "google-genai>=0.5.0",
        "keyring>=24.3.0",
        "cryptography>=41.0.0",
        "pydantic>=2.5.0",
        "psutil>=5.9.0",
        "requests>=2.31.0",
        "tenacity>=8.2.0",
        "ollama>=0.1.0",  # Add ollama to default requirements
    ]

setup(
    name="bgpt-primecodez",
    version="1.0.0",
    author="Nikhil Singh",
    companyname="Primecodez",
    author_email="nikhil@primecodez.com",
    description="Advanced AI Shell Command Assistant",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/primecodez01/bgpt",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Shells",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "ruff>=0.1.0",
            "mypy>=1.8.0",
        ],
        "full": [
            "textual>=0.50.0",
            "prompt-toolkit>=3.0.0",
            "colorama>=0.4.6",
            "pydantic-settings>=2.1.0",
            "watchdog>=3.0.0",
            "httpx>=0.26.0",
            "ollama>=0.1.0",
            "openai>=1.12.0",
            "anthropic>=0.8.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "bgpt=bgpt.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
