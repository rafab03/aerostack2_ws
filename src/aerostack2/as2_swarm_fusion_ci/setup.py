from setuptools import setup

package_name = 'as2_swarm_fusion_ci'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/swarm_ci_fusion.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='Swarm Covariance Intersection fusion node (V1 single target).',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'swarm_ci_fusion_node = as2_swarm_fusion_ci.swarm_ci_fusion_node:main',
        ],
    },
)
