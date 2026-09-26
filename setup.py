from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="mergendb",
    version="0.2.2",
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
    entry_points={
        "console_scripts": [
            "mergen=mergendb.cli.repl:main",
        ],
    },
)
