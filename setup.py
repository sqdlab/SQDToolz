import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sqdtoolz",
    version="0.0.1.dev1",
    author="Prasanna Pakkiam, Rohit Beriwal",
    author_email="p.pakkiam@uq.edu.au, r.beriwal@uq.edu.au",
    description="toolbox to control and run a experiments",
    url="https://github.com/sqdlab/sqdtoolz",
    packages=setuptools.find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        "Programming Language :: Python :: 3 :: ONLY",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    keywords='control toolbox, timing',
    install_requires=['numpy','qcodes>=0.21.0','matplotlib','scipy','pyvisa-py', 'çupy'],
    package_data={
        "sqdtoolz":["Drivers/*.py","HAL/*.py"]
    }
)