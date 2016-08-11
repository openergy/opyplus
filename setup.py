from setuptools import setup

import sys
import os

with open(os.path.join(os.path.dirname(__file__), "oplus", "version.txt")) as f:
    version = f.read().strip()

if sys.argv[-3] == 'tag':
    user = sys.argv[-2]
    pwd = sys.argv[-1]
    print(version)
    os.system('git tag -a %s -m "version %s" ' % (version, version))
    os.system('git tag -d $(git tag --list "jenkins*")')
    #    os.system('git commit -m "version updated via setup.py tag"')
    os.system('git push https://%s:%s@github.com/Openergy/oplus.git --tags' % (user, pwd))
    sys.exit()

setup(
    name='oplus',

    version=version,

    packages=['oplus'],

    author="Geoffroy d'Estaintot",

    author_email="geoffroy.destaintot@openergy.fr",

    long_description=open('README.md').read(),

    install_requires=[
        'pandas',
        'plotly'
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
    ],

    package_data={'oplus': ['*.txt']},

    include_package_data=True
)
