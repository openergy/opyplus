![GitHub](https://img.shields.io/github/license/openergy/opyplus?color=brightgreen)
[![Build Status](https://dev.azure.com/openergy/opyplus/_apis/build/status/openergy.opyplus?branchName=master)](https://dev.azure.com/openergy/opyplus/_build/latest?definitionId=1&branchName=master)
![Azure DevOps coverage](https://img.shields.io/azure-devops/coverage/openergy/opyplus/1)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/opyplus)
![PyPI](https://img.shields.io/pypi/v/opyplus)

# opyplus

opyplus is a package allowing to work with EnergyPlus in Python.

More specifically, it allows to:
* Parse, query and modify idf files efficiently, with a number of checks ensuring that your idf file remains correct
throughout your work
* Parse and create epw files
* Launch simulations on EnergyPlus
* Parse EnergyPlus output files

## Install

To install opyplus, run: `pip install opyplus` or `conda install -c conda-forge opyplus`

## Documentation

Documentation is available at https://opyplus.readthedocs.io

## Compatibility

### Python versions

opyplus is designed to work with python 3.6 and newer.

It is currently automatically tested against the following python versions:
* 3.6
* 3.7

### EnergyPlus versions

opyplus is designed to work with any EnergyPlus version.
Currently, it is automatically tested against the following versions (listed in TESTED_EPLUS_VERSIONS : oplus.tests.util):
* 9.0.1

Each test is therefore run multiple times : once per tested version. To automatically run a test on all versions, use
eplus_tester function (oplus.tests.util).

### Operating system

opyplus is designed to work with any Operating System. It is automatically tested against the latest versions of 
the following OS:
* Ubuntu
* MacOS
* Microsoft Windows

## Contributing

### Local testing

Install pytest and the packages listed in requirements.txt using pip or conda.

Install EnergyPlus v9.0.1.

At the root of the repository, run pytest: `python -m pytest`.

### Flake8

We use flake8 for style enforcement, including docstrings.

To run it, install flake8 and flake8-docstrings using pip or conda.

At the root of the repository, run flake8: `python -m flake8 opyplus/`

### Documentation

To build the configuration:

install the requirements in docs/requirements.txt

run `make html` in opyplus docs directory.

To ensure the examples in the documentation remain up to date, they are tested using the doctest extension:
https://www.sphinx-doc.org/en/master/usage/extensions/doctest.html

run `make doctest` in opyplus docs directory to test the documentation.

When adding code samples to the documentation, please use when possible the doctest extension, as it helps ensure your
samples will be kept up to date: use `.. testcode::` and `.. testoutput::` rather than `.. code-block:: python`.

### Release workflow

1. Developer XX works on his branch (XX-...).
When finished, he completes the RELEASE.md without writing the version number (he completes under ## next).
He then creates a pull request into master.
2. Once the pull request has been accepted by an administrator (tests must pass, among other things), the branch is merged on master.
3. When administrator wants to create a version, he completes RELEASE.md with version number, sets it version.py, commits and creates a tag (vX.X.X).
He then pushes. The tests should succeed because all pull requests tests have succeeded.
A conda and pip build will then automatically be performed by Azure Pipelines. 

