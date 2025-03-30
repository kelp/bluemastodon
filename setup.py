"""Setup script for bluemastodon."""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        name="bluemastodon",
        version="0.9.1",
        description="Automatically cross-post from Bluesky to Mastodon",
        author="Travis Cole",
        author_email="kelp@plek.org",
        url="https://github.com/kelp/bluemastodon",
        packages=find_packages(where="src"),
        package_dir={"": "src"},
        python_requires=">=3.10,<3.14",
        install_requires=[
            "atproto>=0.0.59,<0.1.0",
            "Mastodon.py>=1.8.1,<2.0.0",
            "pydantic>=2.5.3,<3.0.0",
            "python-dotenv>=1.0.0,<2.0.0",
            "loguru>=0.7.2,<1.0.0",
        ],
        entry_points={
            "console_scripts": [
                "bluemastodon=bluemastodon:main",
            ],
        },
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: MIT License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Topic :: Communications",
        ],
    )
