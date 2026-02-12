from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')
    use_sim_time = LaunchConfiguration('use_sim_time')

    q_sigma_arg = DeclareLaunchArgument('q_sigma', default_value='0.25')
    q_sigma = LaunchConfiguration('q_sigma')

    ext_inflate_arg = DeclareLaunchArgument('external_R_inflate', default_value='5.0')
    external_R_inflate = LaunchConfiguration('external_R_inflate')

    gate_arg = DeclareLaunchArgument('use_gating', default_value='true')
    use_gating = LaunchConfiguration('use_gating')

    gate_chi2_arg = DeclareLaunchArgument('gate_chi2', default_value='5.99')
    gate_chi2 = LaunchConfiguration('gate_chi2')

    publish_hz_arg = DeclareLaunchArgument('publish_hz', default_value='20.0')
    publish_hz = LaunchConfiguration('publish_hz')

    time_window_arg = DeclareLaunchArgument('time_window_sec', default_value='1.0')
    time_window_sec = LaunchConfiguration('time_window_sec')

    max_age_arg = DeclareLaunchArgument('max_age_sec', default_value='3.0')
    max_age_sec = LaunchConfiguration('max_age_sec')

    min_sources_arg = DeclareLaunchArgument('min_sources', default_value='1')
    min_sources = LaunchConfiguration('min_sources')

    only_new_arg = DeclareLaunchArgument('publish_only_on_new_ref', default_value='true')
    publish_only_on_new_ref = LaunchConfiguration('publish_only_on_new_ref')

    debug_arg = DeclareLaunchArgument('debug', default_value='true')
    debug = LaunchConfiguration('debug')

    debug_throttle_arg = DeclareLaunchArgument('debug_throttle_sec', default_value='1.0')
    debug_throttle_sec = LaunchConfiguration('debug_throttle_sec')

    drone_list = ['drone0', 'drone1', 'drone2']

    groups = []
    for ns in drone_list:
        groups.append(
            GroupAction([
                PushRosNamespace(ns),
                Node(
                    package='as2_swarm_ekf_people',
                    executable='distributed_ekf_people_node',
                    name='distributed_ekf_people',
                    output='screen',
                    parameters=[{
                        'use_sim_time': use_sim_time,

                        'self_drone': ns,
                        'drones': drone_list,

                        # OJO: ahora consumimos IDs
                        'in_topic_suffix': 'people_with_global_id',

                        'world_frame': 'earth',

                        # Publica /swarm/<self>/ekf_people/id_<ID>
                        'publish_prefix': f'/swarm/{ns}/ekf_people',

                        # EKF params (igual que el tuyo)
                        'q_sigma': q_sigma,
                        'external_R_inflate': external_R_inflate,
                        'use_gating': use_gating,
                        'gate_chi2': gate_chi2,

                        # Ventana temporal
                        'publish_hz': publish_hz,
                        'time_window_sec': time_window_sec,
                        'max_age_sec': max_age_sec,
                        'min_sources': min_sources,
                        'publish_only_on_new_ref': publish_only_on_new_ref,

                        # Debug
                        'debug': debug,
                        'debug_throttle_sec': debug_throttle_sec,
                    }]
                )
            ])
        )

    return LaunchDescription([
        use_sim_time_arg,
        q_sigma_arg,
        ext_inflate_arg,
        gate_arg,
        gate_chi2_arg,
        publish_hz_arg,
        time_window_arg,
        max_age_arg,
        min_sources_arg,
        only_new_arg,
        debug_arg,
        debug_throttle_arg,
        *groups
    ])
