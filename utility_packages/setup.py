import os
from pathlib import Path
from setuptools import setup, find_packages, find_namespace_packages
from pkg_resources import parse_requirements

PACKAGE_INFO = {}
version_file = (Path("src/digma/instrumentation/test_tools") / "version.py").read_text()
exec(version_file, PACKAGE_INFO)

requires = [str(ir) for ir in parse_requirements(Path('requirements.txt').read_text())]

setup(
    name='digma-instrumentation-testtools',
    version=PACKAGE_INFO['__version__'],
    author='Roni Dover',
    author_email='rdover@digma.ai',
    description='Digma instrumentation for Python testing tools',
    long_description=Path("README.md").read_text(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ],
    package_dir={'': 'src'},
    packages=find_namespace_packages('src'),
    include_package_data=True,
    python_requires='>=3.6',
    install_requires=requires,
    url="https://github.com/digma-ai/opentelemetry-instrumentation-digma",
    project_urls={
        'Bug Reports': 'https://github.com/digma-ai/opentelemetry-instrumentation-digma/issues',
        'Source': 'https://github.com/digma-ai/opentelemetry-instrumentation-digma/',
    }
)
