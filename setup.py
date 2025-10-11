from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pyshell-terminal",
    version="1.0.9",  # ⬅ bump version
    author="Yogvid Wankhede",
    author_email="yogvidwankhede@gmail.com",  # must be valid format
    description="A feature-rich, POSIX-compatible shell implemented in Python with advanced scripting capabilities.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yogvidwankhede/PyShell",
    project_urls={
        "Homepage": "https://github.com/yogvidwankhede/PyShell",
        "Website": "https://yogvidwankhede.com", 
        "Github": "https://github.com/yogvidwankhede",
        "LinkedIN": "https://www.linkedin.com/in/yogvid-wankhede-149103231",
        "Documentation": "https://github.com/yogvidwankhede/PyShell/wiki",
        "Bug Reports": "https://github.com/yogvidwankhede/PyShell/issues",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Shells",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
    ],
    packages=find_packages(),
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
)
