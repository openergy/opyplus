from setuptools import setup, find_packages

import sys, os
from oplus.version import __version__


if sys.argv[-1] == 'tag':
    print(__version__)
    os.system('git tag -a %s -m "version %s" ' % (__version__, __version__))
    #    os.system('git commit -m "version updated via setup.py tag"')
    os.system('git push https://EloiLBV:Cython971@github.com/Openergy/oplus.git --tags')
    sys.exit()

setup(
    name='Optimized cython functions',

    version=__version__,

    packages=['oplus'],

    author="Geoffroy d'Estaintot",

    author_email="geoffroy.destaintot@openergy.fr",

    long_description=open('README.md').read(),

    install_requires=[
        'pandas'
        ],

    url='https://github.com/Openergy/oplus',

    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Research & Development",
        "Natural Language :: French",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.4",
        "Topic :: Scientific/Engineering :: Data processing",
    ]

    #    entry_points={
    #    }
)
