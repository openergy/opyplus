from setuptools import setup, find_packages
from pkg_resources import parse_requirements
import os


with open(os.path.join("oplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')


def _get_req_list(file_name):
    with open(file_name) as f:
        return [str(r) for r in parse_requirements(f.read())]


setup(
    name='oplus',

    version=version,

    packages=find_packages(),

    author="Geoffroy d'Estaintot",

    author_email="geoffroy.destaintot@openergy.fr",

    description="A python package for working with Energy Plus",

    long_description=open('README.md').read(),  # long_description,

    install_requires=_get_req_list("requirements-conda.txt") + _get_req_list("requirements-pip.txt"),

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
