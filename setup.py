import os
import sys
from setuptools import setup

# determine setup requirements:
#  - install_requires
#  - tests_require
#  - setup_requires  # for pytest-runner


def read_requirements(requirements_path):
    """
    read requirements from a requirements.txt file
    """

    with open(requirements_path) as f:
        return [
            line.strip() for line in f.read().strip().splitlines()
            if line.strip()
        ]


here = os.path.abspath(os.path.dirname(__file__))
requirements_path = os.path.join(here, 'requirements.txt')
try:
    required_packages = read_requirements(requirements_path)
except IOError:
    print("IOError reading requirements from '{}'".format(requirements_path))
    raise

test_requirements_path = os.path.join(here, 'test-requirements.txt')
try:
    tests_require = read_requirements(test_requirements_path)
except IOError:
    print("IOError reading test requirements from '{}'".format(
        test_requirements_path))
    raise

# add `pytest-runner` distutils plugin for test;
# see https://pypi.python.org/pypi/pytest-runner
setup_requires = []
if {'pytest', 'test', 'ptr'}.intersection(sys.argv[1:]):
    setup_requires.append('pytest-runner')

# invoke `setup` function
setup(
    name='options',
    version='0.1.0',
    packages=['app', 'app.commands'],
    include_package_data=True,
    install_requires=required_packages,
    setup_requires=setup_requires,
    zip_safe=False,
    entry_points='''
        [console_scripts]
        options=app.cli:app
    ''', )
