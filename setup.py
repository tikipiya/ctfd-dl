"""Setup script for CTFd Downloader."""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ctfd-dl",
    version="1.0.2",
    author="tikisan",
    author_email="",
    description="CTFd challenge downloader and organizer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tikipiya/ctfd-dl",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    license="MIT",
    install_requires=[
        "requests>=2.31.0",
        "tqdm>=4.66.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0",
        "urllib3>=2.0.0",
        "pytest>=7.4.0",
        "pytest-mock>=3.12.0",
    ],
    entry_points={
        "console_scripts": [
            "ctfd-dl=ctfd_downloader.main:main",
        ],
    },
)
