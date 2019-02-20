#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from setuptools import Extension
import re


def find_version():
    return re.search(r"^__version__ = '(.*)'$",
                     open('bsdiff/version.py', 'r').read(),
                     re.MULTILINE).group(1)


setup(name='bsdiff',
      version=find_version(),
      description='Binary diff/patch utility.',
      long_description=open('README.rst', 'r').read(),
      author='Erik Moqvist',
      author_email='erik.moqvist@gmail.com',
      license='MIT',
      classifiers=[
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
      ],
      url='https://github.com/eerimoq/bsdiff',
      packages=find_packages(exclude=['tests']),
      ext_modules = [
          Extension(name="bsdiff._sais", sources=["bsdiff/sais.c"])
      ],
      test_suite="tests",
      entry_points = {
          'console_scripts': ['bsdiff=bsdiff.__init__:_main']
      })
