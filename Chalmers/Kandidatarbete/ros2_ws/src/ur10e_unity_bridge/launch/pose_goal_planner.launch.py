from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ur10e_unity_bridge',
            executable='pose_goal_planner',
            output='screen',
            parameters=[{
                'input_topic': '/unity/grasp_target',
                'unity_topic': '/unity/ur10e_joint_trajectory',
                'action_name': '/move_action',
                'group_name': 'ur10e_arm',
                'ee_link': 'wrist_3_link',
                'pipeline_id': 'ompl',
                'planner_id': 'RRTConnectkConfigDefault',
                'allowed_planning_time': 10.0,
                'num_planning_attempts': 10,
                'max_velocity_scaling_factor': 0.35,
                'max_acceleration_scaling_factor': 0.25,
                'position_tolerance': 0.02,
                'orientation_tolerance': 0.12,
            }],
        )
    ])
