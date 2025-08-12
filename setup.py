from setuptools import setup, find_packages

setup(
    name="variance-analysis-anomaly-detection",
    version="1.0.0",
    description="Financial variance analysis and anomaly detection system",
    author="Your Organization",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "numpy>=1.24.0",
        "PyYAML>=6.0",
        "python-dotenv>=1.0.0",
        "xlsxwriter>=3.1.0",
        "colorama>=0.4.6",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "variance-analysis=main:main",
        ],
    },
)