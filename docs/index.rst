Opyplus documentation
=====================

|Licence| |PyPi - Python Version| |PyPI|

.. |Licence| image:: https://img.shields.io/github/license/openergy/opyplus?color=brightgreen
    :target: https://www.mozilla.org/en-US/MPL/2.0/

.. |PyPi - Python Version| image:: https://img.shields.io/pypi/pyversions/opyplus

.. |PyPI| image:: https://img.shields.io/pypi/v/opyplus

**Opyplus** is a package to work with **EnergyPlus in Python**.

With this package, you can programmatically:

 - create and explore input files (building model and weather)
 - run simulations
 - perform outputs analysis

.. note:: Opyplus strongly relies on Python's user-friendly api to offer the **best user experience for thermal engineers**.

Its usage is especially relevant for **automatized and reusable operations**, for example:

 - automatic geometry creation
 - simplified thermal model creation
 - sensitivity analysis


Some of **opyplus strengths** :

 - easy navigation through the thermal model objects
 - auto-check of thermal model consistency when modifications are applied
 - automatic output time-series transformation into Pandas dataframes - a worldwide format used for data analysis

Table of contents
=================

.. toctree::
    :glob:
    :maxdepth: 2

    quickstart/index
    examples/index
    user_guide/index
    api_reference/index
    changelog



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
