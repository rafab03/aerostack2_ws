#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    GroupAction,
    TimerAction,
    DeclareLaunchArgument,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import PushRosNamespace, SetParameter, Node

from ament_index_python.packages import get_package_share_directory



def per_drone_stack(namespace: str, sim_cfg):
    """
    Lanza para un dron:
      - as2_platform_gazebo
      - state_estimator
      - behaviors
      - motion_controller (PID)
    """
    platform_gazebo_share = get_package_share_directory("as2_platform_gazebo")
    state_estimator_share = get_package_share_directory("as2_state_estimator")
    behaviors_share = get_package_share_directory("as2_behaviors_platform")
    motion_controller_share = get_package_share_directory("as2_motion_controller")

    platform = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{platform_gazebo_share}/launch/platform_gazebo_launch.py"
        ),
        launch_arguments={
            "namespace": namespace,
            "simulation_config_file": sim_cfg,
        }.items(),
    )

    estimator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{state_estimator_share}/launch/raw_odometry_state_estimator.launch.py"
        ),
        launch_arguments={
            "namespace": namespace,
            "use_sim_time": "true",
        }.items(),
    )

    behaviors = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{behaviors_share}/launch/as2_platform_behaviors_launch.py"
        ),
        launch_arguments={
            "namespace": namespace,
            "use_sim_time": "true",
        }.items(),
    )

    controller = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{motion_controller_share}/launch/controller_launch.py"
        ),
        launch_arguments={
            "namespace": namespace,
            "use_sim_time": "true",
            "plugin_name": "pid_speed_controller",
        }.items(),
    )

    static_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_tf_base_footprint_to_ns",
        output="screen",
        arguments=[
            "0", "0", "0",          # x y z
            "0", "0", "0",          # yaw pitch roll
            f"{namespace}/base_footprint",  # parent
            f"{namespace}",                 # child
        ],
    )

    return GroupAction(
        actions=[
            PushRosNamespace(namespace),
            SetParameter(name="use_sim_time", value=True),
            static_tf, 
            platform,
            estimator,
            behaviors,
            controller,
        ]
    )


def generate_launch_description():

    sim_cfg_arg = DeclareLaunchArgument(
        "simulation_config_file",
        default_value=(
            "/root/aerostack2_ws/src/aerostack2/"
            "as2_aerial_platforms/as2_platform_gazebo/config/empty_world.yaml"
        ),
        description="Configuración del mundo de simulación",
    )

    sim_cfg = LaunchConfiguration("simulation_config_file")

    # 1) Gazebo / Ignition + spawn de los drones
    gazebo_assets_share = get_package_share_directory("as2_gazebo_assets")
    simulation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            f"{gazebo_assets_share}/launch/launch_simulation.py"
        ),
        launch_arguments={"simulation_config_file": sim_cfg}.items(),
    )

    # 2–5) Stack completo para cada dron
    drone0 = per_drone_stack("drone0", sim_cfg)
    drone1 = per_drone_stack("drone1", sim_cfg)
    drone2 = per_drone_stack("drone2", sim_cfg)

    # Delay para evitar carreras con Gazebo / bridges
    delayed_drones = TimerAction(
        period=5.0,
        actions=[drone0, drone1, drone2],
    )

    return LaunchDescription(
        [
            sim_cfg_arg,
            simulation,
            delayed_drones,
        ]
    )
