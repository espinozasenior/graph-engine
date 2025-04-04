#!/usr/bin/env python3
"""
Setup script for the Graph Engine package.
"""

from setuptools import setup, find_packages
import os

# Get the long description from the README file
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get the version from VERSION file or define it manually
try:
    with open(os.path.join(here, 'VERSION'), encoding='utf-8') as f:
        version = f.read().strip()
except FileNotFoundError:
    version = '0.1.0'  # Initial version

# Get the requirements
with open(os.path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    requirements = [line.strip() for line in f if line.strip()]

setup(
    name='graph-engine',
    version=version,
    description='A tool for analyzing code dependencies and visualizing them as a graph',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Celebr4tion/graph-engine',
    author='Janek Wenning',
    author_email='janek.wenning@gmail.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Other/Proprietary License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    keywords='code analysis, dependency graph, static analysis, dynamic analysis',
    packages=find_packages(exclude=['tests', 'docs', 'examples']),
    python_requires='>=3.10, <4',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'graph-engine-server=graph_core.cli.server:main',
            'graph-engine-snapshot=generate_graph_snapshot:main',
        ],
    },
    project_urls={
        'Bug Reports': 'https://github.com/Celebr4tion/graph-engine/issues',
        'Source': 'https://github.com/Celebr4tion/graph-engine',
    },
) 