#!/usr/bin/env python

# Copyright (c) 2015 - The MITRE Corporation
# For license information, see the LICENSE.txt file

from os.path import abspath, dirname, join
import sys

from setuptools import find_packages, setup

BASE_DIR = dirname(abspath(__file__))
VERSION_FILE = join(BASE_DIR, 'taxii_services', 'version.py')


def get_version():
    with open(VERSION_FILE) as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                version = line.split()[-1].strip('"')
                return version
        raise AttributeError("Package does not have a __version__")


if sys.version_info < (2, 7):
    raise Exception('django-taxii-services requires Python 2.7 or higher.')

install_requires = [
    'Django>=1.11.19',
    'libtaxii>=1.1.105',
    'lxml>=2.2.3',
    'python-dateutil>=1.4.1',
]

with open("README.rst") as f:
    long_description = f.read()

extras_require = {
    'docs': [
        'Sphinx==1.3.1',
        'sphinx_rtd_theme==0.1.8',
    ],
    'test': [
        "tox==1.6.1"
    ],
}

setup(name='taxii_services',
      description='Django TAXII installable app & utilities for creating TAXII Django Web Apps.',
      author='Mark Davidson',
      author_email='mdavidson@mitre.org',
      url="http://taxii.mitre.org/",
      version=get_version(),
      packages=find_packages(),
      install_requires=install_requires,
      extras_require=extras_require,
      long_description=long_description,
      keywords="taxii django taxii_services django-taxii-services",
      classifiers=[
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Topic :: Security',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
      ],
      )
