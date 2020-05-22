import os.path
import sys

from setuptools import setup, find_packages

open_kwds = {}
if sys.version_info > (3,):
    open_kwds['encoding'] = 'utf-8'
profile = os.environ.get('GEOGENIUS_PROFILE', '')
if profile == '':
    requires = []
else:
    req_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "requirements.txt")
    with open(req_path) as f:
        requires = f.read().splitlines()

# with open('README.md', **open_kwds) as f:
#     readme = f.read()

# long_description=readme,

setup(name='geogeniustools',
      version='0.1',
      description='API wrapper and imagery access for the Geogenius Platform',
      classifiers=[],
      keywords='',
      author='Huawei Technology zhaoxianwei',
      author_email='',
      packages=find_packages(exclude=['docs', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      setup_requires=['pytest-runner'],
      tests_require=['pytest', 'vcrpy']
      )
