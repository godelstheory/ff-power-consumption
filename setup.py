import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="energy_consumption",
    version="0.0.1",
    author="Corey Dow-Hygelund",
    author_email="cdowhygelund@mozilla.com",
    description="Run Firefox power consumption experiments.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/godelstheory/FF-power-consumption",
    install_requires=requirements,
    packages=setuptools.find_packages(),
)
