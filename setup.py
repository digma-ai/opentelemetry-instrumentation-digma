import os

from setuptools import setup, find_packages
from pkg_resources import parse_requirements

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, "version.py"), encoding="utf-8") as f:
    PACKAGE_INFO = {}
    exec(f.read(), PACKAGE_INFO)

with open(os.path.join(BASE_DIR, 'README.md'), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(BASE_DIR, 'requirements.txt'), encoding="utf-8") as f:
    requires = [str(ir) for ir in parse_requirements(f.read())]

with open(os.path.join(BASE_DIR, 'test-requirements.txt'), encoding="utf-8") as f:
    requires_test = [str(ir) for ir in parse_requirements(f.read())]
    requires_test.extend(requires)

setup(
    name='opentelemetry-exporter-digma',
    version=PACKAGE_INFO["__version__"],
    author='Roni Dover',
    author_email='rdover@digma.ai',
    description='First step package for digma',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
    package_dir={"": "digma_instrumentation"},
    packages=find_packages("digma_instrumentation"),
    python_requires='>=3.6',
    install_requires=requires,
    test_requires=requires_test,
    project_urls={
        'Bug Reports': 'https://github.com/digma-ai/opentelemetry-exporter-digma/issues',
        'Source': 'https://github.com/digma-ai/opentelemetry-exporter-digma/',
    },
)



