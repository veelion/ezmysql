from setuptools import setup
from ezmysql import __version__

setup(
    name="ezmysql",
    version=__version__,
    packages=['ezmysql'],
    description='Easy way to use mysql in two models: synchronous(pymysql) and asynchronous(aiomysql.Pool) ',
    author="veelion",
    author_email="veelion@gmail.com",
    url='https://github.com/veelion/ezmysql',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    install_requires=[
        'aiomysql',
        'pymysql',
    ],
    license='BSD',
)
