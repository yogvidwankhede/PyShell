from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyshell-terminal",
    version="1.0.1",
    author="Yogvid Wankhede",
    author_website="yogvidwankhede.com",
    author_email="yogvidwankhede@gmail.com",
    description="A feature-rich POSIX-compatible shell implemented in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yogvidwankhede/PyShell",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Shells",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.7",
    install_requires=[
        "readline; platform_system!='Windows'",
        "pyreadline3; platform_system=='Windows'",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=3.0",
            "black>=22.0",
            "flake8>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pyshell=main:repl",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/pyshell/issues",
        "Source": "https://github.com/yourusername/pyshell",
        "Documentation": "https://github.com/yourusername/pyshell/wiki",
    },
)
