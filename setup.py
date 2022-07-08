#!/usr/bin/env python

from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
   name='GEOPHIRES-X',
   version='3.0',
   description='Version 3 of the NREAL-based GEOPHIRES modeling tool.  Now object oriented and extensible.',
   license="MIT",
   long_description=long_description,
   author='Maslcolm Ross',
   author_email='malcolmgti@gmail.com',
   url="https://github.com/malcolm-dsider/GEOPHIRES-X",
   packages=['GEOPHIRES-X'],  #same as name
   install_requires=['numpy', 'numpy-financial', 'mpmath', 'jsons', 'forex_python', 'pint'], #external packages as dependencies
)