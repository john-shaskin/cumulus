#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

requirements = [
    'troposphere',
    'awacs',
    'termcolor',
    'enum34',
]

setup_requirements = ['pytest-runner', ]

test_requirements = [
    'pytest',
    'pytest-runner',
    'stacker',
    'flake8',
    'pytest-watch',
    'pytest-cov',
    'coveralls',
    'awscli',
    'mock',
]

extras = {
    'test': test_requirements,
}

setup(
    author="Brett Swift",
    author_email='brettswift@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Simplified Cloudformation architectural patterns, with an opinion",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='cumulus',
    name='cfn_cumulus',
    packages=find_packages(exclude=['tests']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    extras_require=extras,
    url='https://github.com/brettswift/cumulus',
    version='0.1.10',
    zip_safe=False,
)
