"""Setup/build/install script for STELLADB."""

import os
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="stelladb",
    version="0.1.0",
    description=(
        "Includes functions to upload DESC and VMEC data to the "
        + "stellarator database."
    ),
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/PlasmaControl/Stellarator-Database/",
    author="yigit Gunsur Elmacioglu, Rory Conlin, Dario Panici, Egemen Kolemen",
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
