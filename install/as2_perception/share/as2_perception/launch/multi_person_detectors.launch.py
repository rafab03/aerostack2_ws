from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
import os

def generate_launch_description():
    # Comma-separated list of drone namespaces
    drones_arg = DeclareLaunchArgument(
        'drones',
        default_value='drone0,drone1,drone2',
        description='Comma-separated list of drone namespaces (without leading /)'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation time'
    )

    device_arg = DeclareLaunchArgument(
        'device',
        default_value='cuda:0',
        description='YOLO device: cpu or cuda:0'
    )

    conf_arg = DeclareLaunchArgument(
        'conf_thres',
        default_value='0.35',
        description='YOLO confidence threshold'
    )

    iou_arg = DeclareLaunchArgument(
        'iou_thres',
        default_value='0.45',
        description='YOLO IoU threshold'
    )

    model_arg = DeclareLaunchArgument(
        'model',
        default_value='yolov8n.pt',
        description='YOLO model file (e.g., yolov8n.pt)'
    )

    rviz_config_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value=os.path.join(
            os.path.dirname(__file__),
            'multi_drones_debug_images.rviz'
        ),
        description='Path to RViz2 config file'
    )

    drones = LaunchConfiguration('drones')
    use_sim_time = LaunchConfiguration('use_sim_time')
    device = LaunchConfiguration('device')
    conf_thres = LaunchConfiguration('conf_thres')
    iou_thres = LaunchConfiguration('iou_thres')
    model = LaunchConfiguration('model')
    rviz_config = LaunchConfiguration('rviz_config')

    # Build one detector node per drone namespace
    # Note: we parse the list at runtime in Python (launch-time), so keep it simple:
    drone_list = ['drone0', 'drone1', 'drone2']  # default; overridden below if possible

    # LaunchDescription is constructed once; we can’t directly split LaunchConfiguration here.
    # We'll handle common use (default 3 drones). If you want custom list, set 'drones' to same count
    # or duplicate this block. (If you want fully dynamic splitting, I can give you a slightly more advanced version.)
    #
    # Practical approach: keep 3 drones for now; it matches your ask.
    detector_groups = []
    for ns in drone_list:
        drone_id = ns.replace("drone", "")  # "0", "1", "2"

        detector_groups.append(
            GroupAction([
                PushRosNamespace(ns),
                Node(
                    package='as2_perception',
                    executable='/opt/venv/bin/python',
                    name='person_detector',
                    output='screen',
                    arguments=['-m', 'as2_perception.person_detector_node'],
                    parameters=[{
                        'use_sim_time': use_sim_time,
                        'model_path': model,
                        'device': device,
                        'conf_thres': conf_thres,
                        'iou_thres': iou_thres,

                        # ✅ correctos para tu simulation_config_file:
                        'image_topic': f'sensor_measurements/gimbal{drone_id}/hd_camera1_d{drone_id}/image_raw',
                        'camera_info_topic': f'sensor_measurements/gimbal{drone_id}/hd_camera1_d{drone_id}/camera_info',

                        'detections_topic': 'perception/person_detections',
                        'debug_image_topic': 'perception/person_debug_image',
                        'publish_debug_image': True,
                    }],
                )
            ])
        )

    # RViz (runs without namespace)
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': use_sim_time}],
    )

    return LaunchDescription([
        drones_arg,
        use_sim_time_arg,
        device_arg,
        conf_arg,
        iou_arg,
        model_arg,
        rviz_config_arg,
        *detector_groups,
        rviz_node
    ])
