from setuptools import find_packages, setup


setup(
    name="termbase",
    version="0.1.0",
    description="Short-form IT terminology script generator",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "httpx>=0.27.0",
        "jsonschema>=4.23.0",
        "pydantic>=2.8.0",
        "typer>=0.12.3",
    ],
    python_requires=">=3.12",
)