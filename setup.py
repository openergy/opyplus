from setuptools import setup, find_packages
from pkg_resources import parse_requirements
import os


with open(os.path.join("oplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')


setup(
    name='oplus',
    version=version,
    packages=find_packages(),
    author="Geoffroy d'Estaintot",
    author_email="geoffroy.destaintot@openergy.fr",
    long_description=open('README.md').read(),
    url='https://github.com/Openergy/oplus',
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Natural Language :: French",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    package_data={'oplus': ['*.txt']},
    include_package_data=True
)
