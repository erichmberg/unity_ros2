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
                'repeats': 8,
                'period_s': 0.5,
                'publish_floor': True,
                'publish_rail': True,
                'publish_cell_box': False,
            }],
        ),
    ])
