from setuptools import setup

setup(
    name="WFChessReviewerTdev",
    version="1.0.0",
    description="Automated Chess.com Match Review Helper",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Taam-dev",
    author_email="",
    url="https://github.com/Taam-dev/WFChessReviewerTdev",
    py_modules=["main"],
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
    ],
    entry_points={
        "console_scripts": [
            "wfchess=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment :: Board Games",
        "Operating System :: OS Independent",
    ],
    keywords="chess chess.com automation playwright review",
    license="MIT",
)
