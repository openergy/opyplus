from setuptools import setup, find_packages
from pkg_resources import parse_requirements
import os


with open(os.path.join("oplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')

with open("requirements.txt", "r") as f:
    requirements = [str(r) for r in parse_requirements(f.read())]

setup(
    name='oplus',
    version=version,
    packages=find_packages(),
    author="Openergy development team",
    author_email="contact@openergy.fr",
    long_description=open('README.md').read(),
    install_requires=requirements,
    url='https://github.com/openergy/oplus',
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Natural Language :: French",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    include_package_data=True
)
