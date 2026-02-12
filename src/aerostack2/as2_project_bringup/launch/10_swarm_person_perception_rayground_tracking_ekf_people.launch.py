from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    # ---------- args comunes ----------
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # ---------- args EKF ----------
    q_sigma_arg = DeclareLaunchArgument('q_sigma', default_value='0.25')
    external_R_inflate_arg = DeclareLaunchArgument('external_R_inflate', default_value='5.0')
    use_gating_arg = DeclareLaunchArgument('use_gating', default_value='true')
    gate_chi2_arg = DeclareLaunchArgument('gate_chi2', default_value='5.99')
    publish_hz_arg = DeclareLaunchArgument('publish_hz', default_value='20.0')
    time_window_sec_arg = DeclareLaunchArgument('time_window_sec', default_value='1.0')
    max_age_sec_arg = DeclareLaunchArgument('max_age_sec', default_value='3.0')
    min_sources_arg = DeclareLaunchArgument('min_sources', default_value='1')

    q_sigma = LaunchConfiguration('q_sigma')
    external_R_inflate = LaunchConfiguration('external_R_inflate')
    use_gating = LaunchConfiguration('use_gating')
    gate_chi2 = LaunchConfiguration('gate_chi2')
    publish_hz = LaunchConfiguration('publish_hz')
    time_window_sec = LaunchConfiguration('time_window_sec')
    max_age_sec = LaunchConfiguration('max_age_sec')
    min_sources = LaunchConfiguration('min_sources')

    # ---------- path EKF ----------
    ekf_people_launch = os.path.join(
        get_package_share_directory('as2_swarm_ekf_people'),
        'launch',
        'ekf_people_multi.launch.py'
    )

    return LaunchDescription([
        use_sim_time_arg,

        q_sigma_arg,
        external_R_inflate_arg,
        use_gating_arg,
        gate_chi2_arg,
        publish_hz_arg,
        time_window_sec_arg,
        max_age_sec_arg,
        min_sources_arg,

        # EKF multi-person multi-dron (consume /swarm/<drone>/people_with_global_id)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_people_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'q_sigma': q_sigma,
                'external_R_inflate': external_R_inflate,
                'use_gating': use_gating,
                'gate_chi2': gate_chi2,
                'publish_hz': publish_hz,
                'time_window_sec': time_window_sec,
                'max_age_sec': max_age_sec,
                'min_sources': min_sources,
            }.items()
        ),
    ])
