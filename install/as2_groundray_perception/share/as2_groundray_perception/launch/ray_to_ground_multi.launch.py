from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Ajustes del método
    ground_z_arg = DeclareLaunchArgument('ground_z', default_value='0.0')
    ground_z = LaunchConfiguration('ground_z')

    min_conf_arg = DeclareLaunchArgument('min_conf', default_value='0.35')
    min_conf = LaunchConfiguration('min_conf')

    publish_only_best_arg = DeclareLaunchArgument('publish_only_best', default_value='false')
    publish_only_best = LaunchConfiguration('publish_only_best')

    drone_list = ['drone0', 'drone1', 'drone2']

    groups = []
    for ns in drone_list:
        drone_id = ns.replace("drone", "")

        groups.append(
            GroupAction([
                PushRosNamespace(ns),
                Node(
                    package='as2_groundray_perception',
                    executable='ray_to_ground_node',
                    name='ray_to_ground',
                    output='screen',
                    parameters=[{
                        'use_sim_time': use_sim_time,

                        # inputs relativos al namespace
                        'detections_topic': 'perception/person_detections',
                        'camera_info_topic': f'sensor_measurements/gimbal{drone_id}/hd_camera1_d{drone_id}/camera_info',

                        # TF / suelo
                        'world_frame': 'earth',
                        'camera_frame': f'/{ns}/gimbal{drone_id}/_0/_1/_2/hd_camera1_d{drone_id}/hd_camera/optical_frame',
                        'ground_z': ground_z,

                        # filtro
                        'min_conf': min_conf,
                        'publish_only_best': publish_only_best,

                        # salida global por dron
                        'swarm_out_topic': f'/swarm/{ns}/detections_ray_ground',
                    }]
                )
            ])
        )

    return LaunchDescription([
        use_sim_time_arg,
        ground_z_arg,
        min_conf_arg,
        publish_only_best_arg,
        *groups
    ])
