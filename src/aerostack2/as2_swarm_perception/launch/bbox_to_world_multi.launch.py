from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

def generate_launch_description():
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )

    use_sim_time = LaunchConfiguration('use_sim_time')

    drone_list = ['drone0', 'drone1', 'drone2']

    groups = []
    for ns in drone_list:
        drone_id = ns.replace("drone", "")  # "0","1","2"

        groups.append(
            GroupAction([
                PushRosNamespace(ns),
                Node(
                    package='as2_swarm_perception',
                    executable='bbox_to_world_node',
                    name='bbox_to_world',
                    output='screen',
                    parameters=[{
                        'use_sim_time': use_sim_time,

                        # inputs (relativos al namespace)
                        'detections_topic': 'perception/person_detections',
                        'pose_topic': 'self_localization/pose',

                        # ✅ gimbal por dron (mismo patrón que tu YOLO)
                        'camera_info_topic': f'sensor_measurements/gimbal{drone_id}/hd_camera1_d{drone_id}/camera_info',

                        # output global
                        'swarm_out_topic': f'/swarm/{ns}/detections',

                        # ajustes baseline
                        'min_conf': 0.35,
                        'real_person_height_m': 1.70,
                        'publish_only_best': False,
                    }],
                )
            ])
        )

    return LaunchDescription([
        use_sim_time_arg,
        *groups
    ])
