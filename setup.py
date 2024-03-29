"""Setup/build/install script for STELLADB."""

import os

import versioneer
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r") as f:
    long_description = f.read()

with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="stelladb",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description=(
        "Includes functions to upload DESC and VMEC data to the "
        + "stellarator database."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/PlasmaControl/Stellarator-Database/",
    author="Yigit Gunsur Elmacioglu, Rory Conlin, Dario Panici, Egemen Kolemen",
    author_email="PlasmaControl@princeton.edu",
    license="MIT",
    keywords="stellarator tokamak equilibrium perturbation mhd "
    + "magnetohydrodynamics stability confinement plasma physics "
    + "optimization design fusion data database",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.9",
)
