from setuptools import setup, find_packages
from pkg_resources import parse_requirements
import os


with open(os.path.join("opyplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')

with open("requirements.txt", "r") as f:
    requirements = [str(r) for r in parse_requirements(f.read())]


setup(
    name='opyplus',
    version=version,
    packages=find_packages(where=".", include=["opyplus", "opyplus.*"]),
    description="Python package to work with Energyplus input and output",
    author="Openergy development team",
    author_email="contact@openergy.fr",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    install_requires=requirements,
    url='https://github.com/openergy/opyplus',
    classifiers=[
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    tests_require=[
        'pytest',
        'pytest-cov',
        'pytest-sugar'
    ],
    include_package_data=True
)
