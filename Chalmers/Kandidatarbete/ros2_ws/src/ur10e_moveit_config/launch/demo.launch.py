from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def load_file(package_name, file_path):
    from ament_index_python.packages import get_package_share_directory
    import os
    package_path = get_package_share_directory(package_name)
    abs_file_path = os.path.join(package_path, file_path)
    with open(abs_file_path, 'r') as f:
        return f.read()


def load_yaml(package_name, file_path):
    from ament_index_python.packages import get_package_share_directory
    import os
    import yaml
    package_path = get_package_share_directory(package_name)
    abs_file_path = os.path.join(package_path, file_path)
    with open(abs_file_path, 'r') as f:
        return yaml.safe_load(f)


def generate_launch_description():
    use_gui = LaunchConfiguration('gui')

    urdf_path = PathJoinSubstitution([FindPackageShare('ur_description'), 'urdf', 'ur10e_official.urdf'])
    rviz_config = PathJoinSubstitution([FindPackageShare('ur10e_moveit_config'), 'rviz', 'moveit.rviz'])

    robot_description = {
        'robot_description': ParameterValue(Command(['xacro ', urdf_path]), value_type=str)
    }
    robot_description_semantic = {
        'robot_description_semantic': load_file('ur10e_moveit_config', 'config/ur10e.srdf')
    }

    kinematics_yaml = load_yaml('ur10e_moveit_config', 'config/kinematics.yaml')
    joint_limits_yaml = load_yaml('ur10e_moveit_config', 'config/joint_limits.yaml')
    ompl_yaml = load_yaml('ur10e_moveit_config', 'config/ompl_planning.yaml')
    chomp_yaml = load_yaml('ur10e_moveit_config', 'config/chomp_planning.yaml')
    move_group_yaml = load_yaml('ur10e_moveit_config', 'config/move_group.yaml')
    controllers_yaml = load_yaml('ur10e_moveit_config', 'config/moveit_controllers.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Use joint_state_publisher_gui'),

        Node(package='robot_state_publisher', executable='robot_state_publisher', output='screen', parameters=[robot_description]),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui', output='screen', condition=IfCondition(use_gui)),
        Node(package='tf2_ros', executable='static_transform_publisher', output='screen',
             arguments=['0', '0', '0', '0', '0', '0', 'world', 'base_link']),

        Node(
            package='moveit_ros_move_group',
            executable='move_group',
            output='screen',
            parameters=[
                robot_description,
                robot_description_semantic,
                kinematics_yaml,
                joint_limits_yaml,
                ompl_yaml,
                chomp_yaml,
                move_group_yaml,
                controllers_yaml,
            ],
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[
                robot_description,
                robot_description_semantic,
                kinematics_yaml,
                joint_limits_yaml,
                ompl_yaml,
                chomp_yaml,
            ],
        ),
    ])
