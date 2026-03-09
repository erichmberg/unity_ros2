from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        # RViz plan preview -> Unity trajectory
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

        # Unity grasp target -> staged pick sequence (pregrasp -> grasp -> close -> lift)
        Node(
            package='ur10e_unity_bridge',
            executable='pick_sequence_planner',
            output='screen',
            parameters=[{
                'input_topic': '/unity/grasp_target',
                'unity_topic': '/unity/ur10e_joint_trajectory',
                'action_name': '/move_action',
                'group_name': 'ur10e_arm',
                'ee_link': 'gripper_base_link',
                'pipeline_id': 'ompl',
                'planner_id': 'RRTConnectkConfigDefault',
                'allowed_planning_time': 15.0,
                'num_planning_attempts': 20,
                'max_velocity_scaling_factor': 0.2,
                'max_acceleration_scaling_factor': 0.2,
                'position_tolerance': 0.02,
                'orientation_tolerance': 3.14,
                # Approximate grasp-center offset from gripper base toward finger center
                'grasp_offset_x': 0.0,
                'grasp_offset_y': 0.0,
                'grasp_offset_z': 0.06,
                'pregrasp_lift': 0.10,
                'postgrasp_lift': 0.12,
                'close_width': 0.04,
                'gripper_close_seconds': 1.0,
                'stage_settle_seconds': 0.4,
            }],
        ),

        # Keep floor in planning scene continuously
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
                'size_z': 0.12,
                'z_center': -0.06,
                'repeats': 0,
            }],
        ),
    ])
