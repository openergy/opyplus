from setuptools import setup, find_packages
from pkg_resources import parse_requirements
import os


with open(os.path.join("oplus", "version.py")) as f:
    version = f.read().split("=")[1].strip().strip("'").strip('"')


def _get_req_list(file_name):
    with open(os.path.join(file_name)) as f:
        _, ext = os.path.splitext(file_name)

        if ext not in (".yml", ".yaml"):
            return [str(r) for r in parse_requirements(f.read())]

        # manage yaml
        dependencies = False
        requirements = []
        for line in f.readlines():
            # strip comment, remove spaces
            line = line.split("#")[0].replace(" ", "")

            # skip if empty
            if len(line) == 0:
                continue

            # not yet in dependencies chapter
            if not dependencies:
                if "dependencies:" in line:
                    dependencies = True
                continue

            # in dependency chapter
            if line[0] == "-":
                requirements.append(line[1:])
            else:
                break  # we are changing chapter

        return requirements


setup(
    name='oplus',
    version=version,
    packages=find_packages(),
    author="Geoffroy d'Estaintot",
    author_email="geoffroy.destaintot@openergy.fr",
    long_description=open('README.md').read(),
    install_requires=_get_req_list("requirements-conda.txt") + _get_req_list("requirements-pip.txt"),
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
