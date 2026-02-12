from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():

    # ---------------- Args comunes ----------------
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true'
    )

    drones_arg = DeclareLaunchArgument(
        'drones',
        default_value='drone0,drone1,drone2'
    )

    # ---------------- Args YOLO ----------------
    device_arg = DeclareLaunchArgument(
        'device',
        default_value='cpu'
    )

    conf_arg = DeclareLaunchArgument(
        'conf_thres',
        default_value='0.35'
    )

    iou_arg = DeclareLaunchArgument(
        'iou_thres',
        default_value='0.45'
    )

    model_arg = DeclareLaunchArgument(
        'model',
        default_value='yolov8n.pt'
    )

    # ---------------- Args Ray-to-ground ----------------
    ground_z_arg = DeclareLaunchArgument(
        'ground_z',
        default_value='0.0'
    )

    min_conf_ray_arg = DeclareLaunchArgument(
        'min_conf_ray',
        default_value='0.35'
    )

    publish_only_best_ray_arg = DeclareLaunchArgument(
        'publish_only_best_ray',
        default_value='false'
    )

    # ---------------- Args Tracking/ID ----------------
    gating_dist_arg = DeclareLaunchArgument(
        'gating_dist_m',
        default_value='1.5',
        description='Association gate (meters) for global ID tracking'
    )

    track_timeout_arg = DeclareLaunchArgument(
        'track_timeout_s',
        default_value='1.0',
        description='Seconds without updates before deleting a global track'
    )

    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate_hz',
        default_value='10.0',
        description='Publish rate for /swarm/tracked_persons_global'
    )

    # ---------------- LaunchConfigurations ----------------
    use_sim_time = LaunchConfiguration('use_sim_time')
    drones = LaunchConfiguration('drones')

    device = LaunchConfiguration('device')
    conf_thres = LaunchConfiguration('conf_thres')
    iou_thres = LaunchConfiguration('iou_thres')
    model = LaunchConfiguration('model')

    ground_z = LaunchConfiguration('ground_z')
    min_conf_ray = LaunchConfiguration('min_conf_ray')
    publish_only_best_ray = LaunchConfiguration('publish_only_best_ray')

    gating_dist_m = LaunchConfiguration('gating_dist_m')
    track_timeout_s = LaunchConfiguration('track_timeout_s')
    publish_rate_hz = LaunchConfiguration('publish_rate_hz')

    # ---------------- Paths a launches ----------------
    perception_launch = os.path.join(
        get_package_share_directory('as2_perception'),
        'launch',
        'multi_person_detectors.launch.py'
    )

    ray_ground_launch = os.path.join(
        get_package_share_directory('as2_groundray_perception'),
        'launch',
        'ray_to_ground_multi.launch.py'
    )

    # ---------------- LaunchDescription ----------------
    return LaunchDescription([
        # Args expuestos
        use_sim_time_arg,
        drones_arg,

        device_arg,
        conf_arg,
        iou_arg,
        model_arg,

        ground_z_arg,
        min_conf_ray_arg,
        publish_only_best_ray_arg,

        gating_dist_arg,
        track_timeout_arg,
        publish_rate_arg,

        # 1) YOLO multi-dron
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(perception_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'drones': drones,
                'device': device,
                'conf_thres': conf_thres,
                'iou_thres': iou_thres,
                'model': model,
            }.items()
        ),

        # 2) Ray-to-ground
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(ray_ground_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
                'ground_z': ground_z,
                'min_conf': min_conf_ray,
                'publish_only_best': publish_only_best_ray,
            }.items()
        ),

        # 3) Tracking + IDs globales (UN SOLO NODO para todo el swarm)
        Node(
            package='as2_swarm_person_tracking',
            executable='multi_person_tracker_node',
            name='multi_person_tracker_node',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'drones': drones,
                'input_topic': 'detections_ray_ground',         # relativo a /swarm/<droneX>/
                'output_topic': '/swarm/tracked_persons_global',

                'gating_dist_m': gating_dist_m,
                'track_timeout_s': track_timeout_s,
                'publish_rate_hz': publish_rate_hz,

                # opcional
                'min_hits_to_publish': 1,
            }]
        ),
    ])
