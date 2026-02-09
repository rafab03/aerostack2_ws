#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory

DRONES = ["drone0", "drone1", "drone2"]

def generate_launch_description():
    pkg = get_package_share_directory("as2_behaviors_platform")
    beh_launch = f"{pkg}/launch/as2_platform_behaviors_launch.py"

    actions = []
    for ns in DRONES:
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(beh_launch),
                launch_arguments={
                    "namespace": ns,
                    "use_sim_time": "true",
                }.items(),
            )
        )

    return LaunchDescription(actions)
