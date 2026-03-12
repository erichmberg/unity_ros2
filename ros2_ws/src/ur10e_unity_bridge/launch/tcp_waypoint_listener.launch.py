from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ur10e_unity_bridge',
            executable='tcp_waypoint_listener',
            output='screen',
            parameters=[{
                'bind_host': '0.0.0.0',
                'bind_port': 9100,
                'output_topic': '/unity/grasp_target',
                'frame_id': 'world',
            }],
        ),
    ])
