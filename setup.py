from setuptools import setup
from oplus.version import version
import os

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()


setup(
    name='oplus',

    version=version,

    packages=['oplus'],

    author="Geoffroy d'Estaintot",

    author_email="geoffroy.destaintot@openergy.fr",

    description="A python package for working with Energy Plus",

    long_description=long_description,

    install_requires=[
        'pandas',
        'plotly'
        ],

    url='https://github.com/Openergy/oplus',

    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Natural Language :: French",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.4",
    ],

    keywords=['data', 'simulation'],

    package_data={'oplus': ['*.txt']},

    include_package_data=True
)
