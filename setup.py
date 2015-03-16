from distutils.core import setup

from Cython.Build import cythonize


setup(
    name='Optimized cython functions',
    ext_modules=cythonize("optimize.pyx")
)

# todo: requirements