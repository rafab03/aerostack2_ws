from setuptools import setup

package_name = 'as2_swarm_ekf'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/ekf_multi.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='Distributed EKF fusion for swarm ray-ground detections',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'distributed_ekf_node = as2_swarm_ekf.distributed_ekf_node:main',
        ],
    },
)
