from setuptools import setup, find_packages

import os

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

def get_version():
    init_path = os.path.join("mergendb", "__init__.py")
    if os.path.exists(init_path):
        with open(init_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    return "0.8.1"

setup(
    name="mergendb",
    version=get_version(),
    author="Uğur Türker Kebeci",
    author_email="ugurturkerkebeci@users.noreply.github.com",
    description="Ultra-compact, columnar, embedded database engine designed to run large workloads on small hardware.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ugurturkerkebeci/MergenDB",
    project_urls={
        "Bug Tracker": "https://github.com/ugurturkerkebeci/MergenDB/issues",
        "Source Code": "https://github.com/ugurturkerkebeci/MergenDB",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Database :: Database Engines/Servers",
    ],
    python_requires=">=3.8",
    extras_require={
        "studio": ["mergendb-studio>=0.7.0"],
    },
    entry_points={
        "console_scripts": [
            "mergen=mergendb.cli.repl:main",
            "mergendb=mergendb.cli.repl:main",
            "mergendb-server=mergendb.server.server:main",
        ],
    },
)
