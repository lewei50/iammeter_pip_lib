"""Build the independently versioned asynchronous IAMMETER library."""

from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="iammeter",
    version="0.3.0",
    author="yangbo1979",
    author_email="gyangbo@gmail.com",
    description="IAMMETER local HTTP client with asynchronous and legacy synchronous APIs",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/lewei50/iammeter_pip_lib",
    packages=find_packages(),
    package_data={"iammeter": ["py.typed"]},
    python_requires=">=3.11",
    install_requires=["aiohttp>=3.14.5", "requests>=2.20.0", "voluptuous>=0.13.1"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
