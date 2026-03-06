from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    use_gui = LaunchConfiguration('gui')
    urdf_path = PathJoinSubstitution([FindPackageShare('ur_description'), 'urdf', 'ur10e_official.urdf'])
    rviz_config = PathJoinSubstitution([FindPackageShare('ur_description'), 'rviz', 'ur10e.rviz'])
    robot_description = {'robot_description': ParameterValue(Command(['xacro ', urdf_path]), value_type=str)}
    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Use joint_state_publisher_gui'),
        Node(package='robot_state_publisher', executable='robot_state_publisher', output='screen', parameters=[robot_description]),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui', output='screen', condition=IfCondition(use_gui)),
        Node(package='rviz2', executable='rviz2', name='rviz2', output='screen', arguments=['-d', rviz_config]),
    ])
