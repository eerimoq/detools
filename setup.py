#!/usr/bin/env python3

import setuptools
from setuptools import find_packages
from setuptools import Extension
import re


def find_version():
    return re.search(r"^__version__ = '(.*)'$",
                     open('detools/version.py', 'r').read(),
                     re.MULTILINE).group(1)


def setup(ext_modules):
    setuptools.setup(
        name='detools',
        version=find_version(),
        description='Binary delta encoding tools.',
        long_description=open('README.rst', 'r').read(),
        author='Erik Moqvist',
        author_email='erik.moqvist@gmail.com',
        license='BSD',
        classifiers=[
            'License :: OSI Approved :: BSD License',
            'Programming Language :: Python :: 3',
        ],
        url='https://github.com/eerimoq/detools',
        packages=find_packages(exclude=['tests']),
        install_requires=[
            'humanfriendly',
            'bitstruct'
        ],
        ext_modules=ext_modules,
        test_suite="tests",
        entry_points = {
            'console_scripts': ['detools=detools.__init__:_main']
        })


try:
    setup([
        Extension(name="detools.csais", sources=["detools/sais.c"]),
        Extension(name="detools.cbsdiff", sources=["detools/bsdiff.c"])
    ])
except:
    print('WARNING: Failed to build the C extension.')
    setup([])
