from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')
    q_sigma_arg = DeclareLaunchArgument('q_sigma', default_value='0.25')
    external_R_inflate_arg = DeclareLaunchArgument('external_R_inflate', default_value='1.5')
    use_gating_arg = DeclareLaunchArgument('use_gating', default_value='true')
    gate_chi2_arg = DeclareLaunchArgument('gate_chi2', default_value='5.99')
    max_age_sec_arg = DeclareLaunchArgument('max_age_sec', default_value='1.0')

    use_sim_time = LaunchConfiguration('use_sim_time')
    q_sigma = LaunchConfiguration('q_sigma')
    external_R_inflate = LaunchConfiguration('external_R_inflate')
    use_gating = LaunchConfiguration('use_gating')
    gate_chi2 = LaunchConfiguration('gate_chi2')
    max_age_sec = LaunchConfiguration('max_age_sec')

    ekf_launch = os.path.join(
        get_package_share_directory('as2_swarm_ekf'),
        'launch',
        'ekf_multi.launch.py'
    )

    return LaunchDescription([
        use_sim_time_arg,
        q_sigma_arg,
        external_R_inflate_arg,
        use_gating_arg,
        gate_chi2_arg,
        max_age_sec_arg,

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ekf_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'q_sigma': q_sigma,
                'external_R_inflate': external_R_inflate,
                'use_gating': use_gating,
                'gate_chi2': gate_chi2,
                'max_age_sec': max_age_sec,
            }.items()
        ),
    ])
