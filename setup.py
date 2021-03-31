from setuptools import setup, find_packages

setup(
    name='github_secret_finder',
    version='2.0.0',
    description='Script to monitor commits from Github users and organizations for secrets.',
    url='https://github.com/gsoft-inc/github-secret-finder',
    author='Mathieu Gascon-Lefebvre',
    author_email='mathieuglefebvre@gmail.com',
    license='Apache',
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={'github_secret_finder': ['data/*']},
    install_requires=[
        'unidiff',
        'requests',
        'detect_secrets',
        'sqlitedict'
    ],
    entry_points={
        'console_scripts': ['github-secret-finder = github_secret_finder.main:main'],
    },
)
