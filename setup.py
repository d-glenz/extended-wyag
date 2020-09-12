import setuptools

setuptools.setup(
    name='ewyag',
    version='1.0',
    author='Dominik Glenz',
    author_email='dominik.glenz@gmail.com',
    description='Write Yourself a Git! - extended',
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': ['ewyag=ewyag.main:main'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
