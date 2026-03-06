from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
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
                'id': 'floor',
                'size_x': 4.0,
                'size_y': 4.0,
                'size_z': 0.10,
                'z_center': -0.12,
                'repeats': 10,
            }],
        ),
    ])
