from setuptools import setup, find_packages

import sys
import os
from oplus.version import version


if sys.argv[-1] == 'tag':
    print(version)
    os.system('git tag -a %s -m "version %s" ' % (version, version))
    #    os.system('git commit -m "version updated via setup.py tag"')
    os.system('git push https://EloiLBV:Cython971@github.com/Openergy/oplus.git --tags')
    sys.exit()

setup(
    name='Openergy oplus',

    version=version,

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
)
