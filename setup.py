from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
import os
import subprocess


with open(os.path.join("oplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')


_cmd = "conda install -y --file conda-requirements.txt".split(" ")


class OInstall(install):
    def run(self):
        subprocess.call("conda install -y --file conda-requirements.txt".split(" "))
        install.run(self)


class ODevelop(develop):
    def run(self):
        subprocess.call(_cmd)
        develop.run(self)


setup(
    name='oplus',

    version=version,

    packages=find_packages(),

    author="Geoffroy d'Estaintot",

    author_email="geoffroy.destaintot@openergy.fr",

    description="A python package for working with Energy Plus",

    long_description=open('README.md').read(),  # long_description,

    install_requires=[
        'plotly>=1.9.6,<2.0.0',
        "nose-exclude>=0.4.1,<1.0.0"  # for tests
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

    include_package_data=True,

    cmdclass=dict(install=OInstall, develop=ODevelop)
)
