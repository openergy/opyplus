![GitHub](https://img.shields.io/github/license/openergy/opyplus?color=brightgreen)

[![Build Status](https://dev.azure.com/openergy/opyplus/_apis/build/status/openergy.opyplus?branchName=master)](https://dev.azure.com/zachariebrodard/opyplus/_build/latest?definitionId=1&branchName=master)

![Azure DevOps coverage](https://img.shields.io/azure-devops/coverage/openergy/opyplus/1)



# opyplus

opyplus is a python package is a package that can be used to work with EnergyPlus in Python.

More specifically, it allows to:
* Parse, query and modify idf files efficiently, with a number of checks ensure that your idf file remains correct
throughout your work
* Parse and create epw files
* Launch simulations on EnergyPlus
* Parse EnergyPlus output files

## Documentation


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
