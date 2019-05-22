"""The setup script."""

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ["grpcio", "protobuf", "grpcio-tools", "jinja2", "pyyaml"]

setup_requirements = []

test_requirements = []

setup(
    author="GuangTian Li",
    author_email='guangtian_li@qq.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="The Python micro framework for building gPRC application.",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    include_package_data=True,
    keywords='grpcalchemy',
    name='grpcalchemy',
    packages=['grpcalchemy', 'grpcalchemy.templates'],
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/GuangTianLi/grpcalchemy',
    python_requires='>=3.6.0',
    version='0.2.9',
    zip_safe=False,
)
