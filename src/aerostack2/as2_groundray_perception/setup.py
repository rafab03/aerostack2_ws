from setuptools import setup
from glob import glob
import os

package_name = 'as2_groundray_perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools', 'numpy'],
    zip_safe=True,
    maintainer='rafa',
    maintainer_email='rafa@todo.todo',
    description='Ray-to-ground person localization from 2D detections using TF',
    license='TODO',
    entry_points={
        'console_scripts': [
            'ray_to_ground_node = as2_groundray_perception.ray_to_ground_node:main',
        ],
    },
)