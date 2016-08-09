from setuptools import setup

import sys, os
from oplus.version import version as __version__


def abcdert():
    if sys.argv[-3] == 'tag':
        user = sys.argv[-2]
        pwd = sys.argv[-1]
        print(__version__)
        os.system('git tag -a %s -m "version %s" ' % (__version__, __version__))
        #    os.system('git commit -m "version updated via setup.py tag"')
        os.system('git push https://%s:%s@github.com/Openergy/oplus.git --tags' % (user, pwd))
        sys.exit()

setup(
    name='oplus',

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

# todo: requirements
