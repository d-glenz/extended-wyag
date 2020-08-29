import setuptools

setuptools.setup(
    name='wyag',
    version='1.0',
    author='Thibault Polge',
    author_email='thibault@thb.lt',
    description='Write Yourself a Git!',
    packages=setuptools.find_packages(),
    install_requires=[
        'argcomplete'
    ],
    entry_points={
        'console_scripts': ['wyag=wyag.main:main'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
