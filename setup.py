# setup.py
# ============================================
# Prizolov Sports AI - Setup
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

from setuptools import setup, find_packages

setup(
    name="prizolov-sports-ai",
    version="0.1.0",
    description="Sports data and prediction module for Prizolov Agent OS",
    author="Dm.Andreyanov",
    packages=find_packages(),
    install_requires=[
        # Добавьте зависимости, которые нужны вашему модулю, например:
        # "requests",
        # "pandas",
    ],
    python_requires=">=3.8",
)
