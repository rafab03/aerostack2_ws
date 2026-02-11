from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():

    # Args comunes
    use_sim_time_arg = DeclareLaunchArgument('use_sim_time', default_value='true')
    drones_arg = DeclareLaunchArgument('drones', default_value='drone0,drone1,drone2')

    # Args YOLO
    device_arg = DeclareLaunchArgument('device', default_value='cpu')
    conf_arg = DeclareLaunchArgument('conf_thres', default_value='0.35')
    iou_arg = DeclareLaunchArgument('iou_thres', default_value='0.45')
    model_arg = DeclareLaunchArgument('model', default_value='yolov8n.pt')

    use_sim_time = LaunchConfiguration('use_sim_time')
    drones = LaunchConfiguration('drones')
    device = LaunchConfiguration('device')
    conf_thres = LaunchConfiguration('conf_thres')
    iou_thres = LaunchConfiguration('iou_thres')
    model = LaunchConfiguration('model')

    # Paths a los launch de otros paquetes
    perception_launch = os.path.join(
        get_package_share_directory('as2_perception'),
        'launch',
        'multi_person_detectors.launch.py'
    )

    swarm_launch = os.path.join(
        get_package_share_directory('as2_swarm_perception'),
        'launch',
        'bbox_to_world_multi.launch.py'
    )

    return LaunchDescription([
        use_sim_time_arg, drones_arg,
        device_arg, conf_arg, iou_arg, model_arg,

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

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(swarm_launch),
            launch_arguments={
                'use_sim_time': use_sim_time,
            }.items()
        ),
    ])
