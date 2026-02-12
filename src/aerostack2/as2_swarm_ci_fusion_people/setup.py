from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'as2_swarm_ci_fusion_people'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', 'as2_swarm_ci_fusion_people', 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='rafaelblancolopez03@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'swarm_ci_fusion_people_node = as2_swarm_ci_fusion_people.swarm_ci_fusion_people_node:main',
        ],
    },
)
