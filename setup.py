from setuptools import setup, find_packages

setup(
    name='Controller',
    version='0.1',
    packages=find_packages(),
    install_requires=[],  # Add dependencies if needed
    entry_points={
        'console_scripts': [],  # Add console scripts if needed
    },
    author='Kyro744',
    author_email='your_email@example.com',
    description='A Python package for Controller.',
    long_description=open('README.md').read(),  # Ensure this file exists
    long_description_content_type='text/markdown',
    url='https://github.com/Kyro744/Controller',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
)