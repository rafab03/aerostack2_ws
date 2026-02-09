#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory

DRONES = ["drone0", "drone1", "drone2"]

def generate_launch_description():
    sim_cfg_arg = DeclareLaunchArgument(
        "simulation_config_file",
        default_value="/root/aerostack2_ws/src/aerostack2/as2_aerial_platforms/as2_platform_gazebo/config/empty_world.yaml",
    )
    sim_cfg = LaunchConfiguration("simulation_config_file")

    pkg = get_package_share_directory("as2_platform_gazebo")
    platform_launch = f"{pkg}/launch/platform_gazebo_launch.py"

    actions = [sim_cfg_arg]
    for ns in DRONES:
        actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(platform_launch),
                launch_arguments={
                    "namespace": ns,
                    "simulation_config_file": sim_cfg,

                    # 🔥 fuerza por dron (NO defaults compartidos)
                    "cmd_vel_topic": f"/gz/{ns}/cmd_vel",
                    "arm_topic": f"/gz/{ns}/arm",
                    "acro_topic": f"/gz/{ns}/acro",
                }.items(),
            )
        )

    return LaunchDescription(actions)
