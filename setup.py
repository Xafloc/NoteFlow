from setuptools import setup, find_packages

setup(
    name='noteflow',
    version='0.1.1',
    author='@Xafloc',
    author_email='xafloc@tetrago.com',
    description='A simple one-big-note app with Markdown support',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/Xafloc/NoteFlow',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'fastapi',
        'uvicorn',
        'markdown-it-py',
        'requests>=2.31.0',
        'beautifulsoup4>=4.12.0',
        'pydantic',
        'python-multipart',
    ],
    entry_points={
        'console_scripts': [
            'noteflow=noteflow.noteflow:main',
        ],
    },
    package_data={
        'noteflow': ['fonts/*', 'static/*'],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
) 