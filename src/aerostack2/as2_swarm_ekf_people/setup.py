from setuptools import setup
import os
from glob import glob

package_name = 'as2_swarm_ekf_people'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='rafaelblancolopez03@gmail.com',
    description='Distributed EKF multi-person (per global ID).',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'distributed_ekf_people_node = as2_swarm_ekf_people.distributed_ekf_people_node:main',
        ],
    },
)
