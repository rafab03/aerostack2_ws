#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

DRONES = ["drone0", "drone1", "drone2"]

def generate_launch_description():
    plugin_arg = DeclareLaunchArgument(
        "plugin_name",
        default_value="pid_speed_controller",
        description="Plugin del controlador de movimiento",
    )
    plugin = LaunchConfiguration("plugin_name")

    pkg = get_package_share_directory("as2_motion_controller")
    ctrl_launch = f"{pkg}/launch/controller_launch.py"

    actions = [plugin_arg]
    for ns in DRONES:
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(ctrl_launch),
                launch_arguments={
                    "namespace": ns,
                    "use_sim_time": "true",
                    "plugin_name": plugin,
                }.items(),
            )
        )

    return LaunchDescription(actions)

