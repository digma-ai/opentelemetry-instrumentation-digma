import os
from pathlib import Path
from setuptools import setup, find_packages
from pkg_resources import parse_requirements

PACKAGE_INFO = {}
version_file = (Path("digma_instrumentation") / "version.py").read_text()
exec(version_file, PACKAGE_INFO)

requires = [str(ir) for ir in parse_requirements(Path('requirements.txt').read_text())]

setup(
    name='opentelemetry-instrumentation-digma',
    version=PACKAGE_INFO['__version__'],
    author='Roni Dover',
    author_email='rdover@digma.ai',
    description='First step package for digma',
    long_description=Path("README.md").read_text(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
    packages=find_packages(),
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=requires,
    project_urls={
        'Bug Reports': 'https://github.com/digma-ai/opentelemetry-exporter-digma/issues',
        'Source': 'https://github.com/digma-ai/opentelemetry-exporter-digma/',
    },
)



