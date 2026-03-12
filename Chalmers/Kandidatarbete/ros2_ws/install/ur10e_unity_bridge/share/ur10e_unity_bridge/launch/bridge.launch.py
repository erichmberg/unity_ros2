from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    publish_mesh = LaunchConfiguration('publish_mesh')

    return LaunchDescription([
        DeclareLaunchArgument(
            'publish_mesh',
            default_value='false',
            description='Publish heavy Rita cell STL collision mesh into MoveIt planning scene',
        ),
        Node(
            package='ur10e_unity_bridge',
            executable='display_to_unity',
            output='screen',
            parameters=[{
                'input_topic': '/display_planned_path',
                'unity_topic': '/unity/ur10e_joint_trajectory',
                'publish_on_every_plan': True,
            }],
        ),
        Node(
            package='ur10e_unity_bridge',
            executable='floor_collision_publisher',
            output='screen',
            parameters=[{
                'topic': '/collision_object',
                'frame_id': 'world',
                'repeats': 8,
                'period_s': 0.5,
                'publish_floor': True,
                'publish_rail': True,
                'publish_cell_box': False,
            }],
        ),
        Node(
            package='ur10e_unity_bridge',
            executable='mesh_collision_publisher',
            output='screen',
            condition=IfCondition(publish_mesh),
            parameters=[{
                'topic': '/collision_object',
                'frame_id': 'world',
                'id': 'rita_cell_mesh',
                'mesh_path': '~/EricBerg/Chalmers/Kandidatarbete/UR10e_ROS2_Baseline/Assets/Environment/RITA CELL.stl',
                'scale': 1.0,
                'x': 0.0,
                'y': 0.0,
                'z': 0.0,
                'qx': 0.0,
                'qy': 0.0,
                'qz': 0.0,
                'qw': 1.0,
                'repeats': 8,
                'period_s': 0.5,
            }],
        ),
    ])
