from setuptools import setup

package_name = 'ur10e_unity_bridge'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/bridge.launch.py', 'launch/pose_goal_planner.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Eric Berg',
    maintainer_email='eric@example.com',
    description='Bridge MoveIt planned trajectories to Unity joint trajectory topic',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'display_to_unity = ur10e_unity_bridge.display_to_unity:main',
            'floor_collision_publisher = ur10e_unity_bridge.floor_collision_publisher:main',
            'pose_goal_planner = ur10e_unity_bridge.pose_goal_planner:main',
        ],
    },
)
