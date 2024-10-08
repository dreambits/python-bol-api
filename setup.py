import sys
from setuptools import setup, find_packages

import bol

def readme():
    with open('README.rst') as f:
        return f.read()

# Dynamically calculate the version based on actistream.VERSION.
VERSION = bol.__version__
IS_PY2 = sys.version_info[0] < 3

install_requires = [
    'python-dateutil',
    'requests']
if IS_PY2:
    install_requires.append('enum34')

setup(name='python-bol-api-latest',
      version=VERSION,
      description="Wrapper for the bol.com API",
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'Operating System :: OS Independent',
          'Topic :: Software Development',
          'Topic :: System',
          'Topic :: System :: Software Distribution',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.8',
          'License :: OSI Approved :: '
          'GNU Lesser General Public License v3 or later (LGPLv3+)',
      ],
      keywords='bol bol.com api wrapper',
      author='Raymond Penners, Dreambits Technologies Pvt. Ltd.',
      author_email='office@dreambits.in',
      url='https://dreambits.in',
      long_description=readme(),
      long_description_content_file="text/x-rst",
      license='',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points="")
