from setuptools import setup, find_packages

setup(
    name="lively",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "lively": ["static/*"]
    },
    install_requires=[
        "fastapi>=0.110.0",
        "uvicorn[standard]>=0.28.0",
        "websockets>=12.0",
        "pydantic>=2.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "lively = lively.cli:main",
        ],
    },
)
