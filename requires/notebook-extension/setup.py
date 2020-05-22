#!/usr/bin/env python
"""Setup script for geogenius_jupyter_notebook_extensions."""

from setuptools import find_packages, setup

setup(
    name='geogenius_jupyter_notebook_extensions',
    version='0.1.0',
    description='geogenius jupyter notebook extensions',
    author='geogenius',
    author_email='geogenius@gmail.com',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        "console_scripts":[
            'set_config = geogenius_jupyter_notebook_extensions.set_config:main'
        ]
    },
    include_package_data=True,
    zip_safe=False,
)