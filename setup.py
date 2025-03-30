from setuptools import setup, find_packages

setup(
    name="test_framework",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "playwright==1.42.0",
        "requests==2.31.0",
        "pytest==8.0.2",
        "pytest-asyncio==0.23.5",
        "pytest-playwright==1.42.0",
        "allure-pytest==2.13.2",
        "PyYAML==6.0.1",
        "Faker==24.1.0",
        "opencv-python==4.9.0.80",
        "numpy==1.26.4",
        "loguru==0.7.2",
        "jinja2==3.1.3",
        "python-dotenv==1.0.1",
        "tenacity==8.2.3"
    ],
    python_requires=">=3.8",
) 