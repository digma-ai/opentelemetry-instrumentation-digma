import setuptools
import os

from pkg_resources import parse_requirements

BASE_DIR = os.path.dirname(__file__)
VERSION_FILENAME = os.path.join(
    BASE_DIR, "src", "opentelemetry", "exporter", "digma", "version.py"
)

PACKAGE_INFO = {}
with open(VERSION_FILENAME, encoding="utf-8") as f:
    exec(f.read(), PACKAGE_INFO)

with open("requirements.txt", "r") as fh:
    install_requires = [str(r) for r in parse_requirements(fh.readlines())]

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(version=PACKAGE_INFO["__version__"], install_requires=install_requires, long_description=long_description)



