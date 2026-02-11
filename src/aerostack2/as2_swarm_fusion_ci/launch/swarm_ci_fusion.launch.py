from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    drones_arg = DeclareLaunchArgument(
        'drones',
        default_value='["drone0","drone1","drone2"]',
        description='List of drone namespaces as a Python/JSON list string.'
    )

    out_topic_arg = DeclareLaunchArgument(
        'out_topic',
        default_value='/swarm/fused_target',
        description='Output topic for fused PoseWithCovarianceStamped.'
    )

    sync_slop_arg = DeclareLaunchArgument(
        'sync_slop_sec',
        default_value='0.75',
        description='Max time difference between measurements to fuse.'
    )

    max_age_arg = DeclareLaunchArgument(
        'max_age_sec',
        default_value='10.0',
        description='Discard measurements older than this.'
    )

    node = Node(
        package='as2_swarm_fusion_ci',
        executable='swarm_ci_fusion_node',
        name='swarm_ci_fusion_node',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'drones': LaunchConfiguration('drones'),
            'in_topic_suffix': 'detections_ray_ground',
            'out_topic': LaunchConfiguration('out_topic'),
            'world_frame': 'earth',
            'time_window_sec': LaunchConfiguration('sync_slop_sec'),
            'max_age_sec': LaunchConfiguration('max_age_sec'),
            'min_drones': 2,
            'w_steps': 200,
            'criterion': 'det',
        }]
    )

    return LaunchDescription([
        drones_arg,
        out_topic_arg,
        sync_slop_arg,
        max_age_arg,
        node
    ])
