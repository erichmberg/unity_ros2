# MoveIt -> Unity bridge (Option A)

This bridge subscribes to MoveIt DisplayTrajectory and republishes as
`trajectory_msgs/JointTrajectory` on `/unity/ur10e_joint_trajectory`.

## Build
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ur10e_unity_bridge ur10e_moveit_config ur_description --allow-overriding ur_description
source install/setup.bash
```

## Run (3 terminals)

### Terminal A: Unity ROS TCP endpoint
```bash
cd ~/unity_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

### Terminal B: MoveIt demo
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_moveit_config demo.launch.py
```

### Terminal C: Bridge
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_unity_bridge bridge.launch.py
```

Now, in RViz MotionPlanning: click **Plan**.
The bridge will immediately publish planned trajectory to Unity topic.
