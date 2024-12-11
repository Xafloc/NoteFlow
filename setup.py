from setuptools import setup, find_packages

setup(
    name='noteflow',
    version='0.3.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'fastapi>=0.104.1',
        'uvicorn>=0.24.0',
        'markdown-it-py>=3.0.0',
        'mdit-py-plugins',
        'requests>=2.31.0',
        'beautifulsoup4>=4.12.0',
        'pydantic>=2.4.2',
        'python-multipart>=0.0.6',
        'jinja2>=3.1.2',
        'platformdirs>=3.0.0',
        'psutil>=5.9.5',
    ],
    entry_points={
        'console_scripts': [
            'noteflow=noteflow.noteflow:main',
        ],
    },
    package_data={
        'noteflow': ['fonts/*', 'static/*'],
    },
) 