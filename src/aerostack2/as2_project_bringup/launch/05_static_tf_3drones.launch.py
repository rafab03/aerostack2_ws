#!/usr/bin/env python3
from launch import LaunchDescription
from launch_ros.actions import Node

DRONES = ["drone0", "drone1", "drone2"]

def generate_launch_description():
    actions = []
    for ns in DRONES:
        actions.append(
            Node(
                package="tf2_ros",
                executable="static_transform_publisher",
                name=f"static_tf_base_footprint_to_{ns}",
                output="screen",
                arguments=[
                    "0", "0", "0",
                    "0", "0", "0",
                    f"{ns}/base_footprint",
                    f"{ns}",
                ],
            )
        )
    return LaunchDescription(actions)
