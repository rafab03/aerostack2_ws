from setuptools import find_packages
from setuptools import setup

setup(
    name='as2_swarm_person_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('as2_swarm_person_interfaces', 'as2_swarm_person_interfaces.*')),
)
