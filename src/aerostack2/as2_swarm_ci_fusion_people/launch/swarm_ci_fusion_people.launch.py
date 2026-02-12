from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')

    drones_arg = DeclareLaunchArgument('drones', default_value='drone0,drone1,drone2')
    stale_arg = DeclareLaunchArgument('stale_window_s', default_value='0.8')
    min_sources_arg = DeclareLaunchArgument('min_sources', default_value='2')
    rate_arg = DeclareLaunchArgument('publish_rate_hz', default_value='10.0')
    wsteps_arg = DeclareLaunchArgument('w_steps', default_value='101')
    criterion_arg = DeclareLaunchArgument('criterion', default_value='logdet')

    ci_node = Node(
        package='as2_swarm_ci_fusion_people',
        executable='swarm_ci_fusion_people_node',
        name='swarm_ci_fusion_people_node',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'drones': LaunchConfiguration('drones'),
            'input_suffix': 'people_with_global_id',
            'output_topic': '/swarm/people_ci_fused',
            'stale_window_s': LaunchConfiguration('stale_window_s'),
            'min_sources': LaunchConfiguration('min_sources'),
            'publish_rate_hz': LaunchConfiguration('publish_rate_hz'),
            'w_steps': LaunchConfiguration('w_steps'),
            'criterion': LaunchConfiguration('criterion'),
        }]
    )

    return LaunchDescription([
        use_sim_time_arg,
        drones_arg,
        stale_arg,
        min_sources_arg,
        rate_arg,
        wsteps_arg,
        criterion_arg,
        ci_node
    ])
