![GitHub](https://img.shields.io/github/license/openergy/opyplus?color=brightgreen)
[![test-and-publish](https://github.com/openergy/opyplus/actions/workflows/opypackage-standard.yml/badge.svg?branch=cc_3_12)](https://github.com/openergy/opyplus/actions/workflows/opypackage-standard.yml)
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

opyplus is designed to work with python 3.8 and newer.

It is currently automatically tested against the following python versions:
* 3.10
* 3.11
* 3.12

### EnergyPlus versions

opyplus is designed to work with any EnergyPlus version.
Currently, it is automatically tested against the following versions (listed in TESTED_EPLUS_VERSIONS : oplus.tests.util):
* 22.1.0

Each test is therefore run multiple times : once per tested version. To automatically run a test on all versions, use
eplus_tester function (oplus.tests.util).

### Operating system

opyplus is designed to work with any Operating System but is automatically tested against the latest versions of Ubuntu OS.

## Contributing

### Local testing

Install pytest and the packages listed in requirements.txt using pip or conda.

Install EnergyPlus v22.1.0.

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
He then creates a pull request into develop.
2. Once the pull request has been accepted by an administrator the branch is merged on develop. Since new version is "next": only tests are running
3. When administrator wants to create a version, on branch "develop" he completes RELEASE.md with version number "x.x.x".
He then pushes. Tests and versioning are running. A conda and pip build will then automatically be performed by Github actions. 
