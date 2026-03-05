# UR10e ROS2 Baseline — Setup

## Included
- `Assets/robot/ur10e_official.urdf`
- `Assets/robot/ur_description/meshes/ur10e/*`
- `Assets/robot/ur_description/meshes/gripper/*`
- `Assets/Scripts/JointTrajectoryToUr10e.cs`
- `Assets/Scripts/AutoAnchorArticulationRoots.cs`

## Unity
1. Open this project in Unity.
2. Let Package Manager resolve robotics packages from `Packages/manifest.json`.
3. Import `Assets/robot/ur10e_official.urdf` into scene.
4. Add `JointTrajectoryToUr10e` to robot root.
5. Press Play.

## ROS2 (Humble)
### Endpoint
```bash
cd ~/unity_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

### Test command
```bash
source /opt/ros/humble/setup.bash
ros2 topic pub --once /unity/ur10e_joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint','left_finger_joint','right_finger_joint'],
  points: [
    { positions: [0.0,-1.57,1.57,0.0,0.0,0.0,0.0,0.0], time_from_start: {sec:0, nanosec:0} },
    { positions: [0.7,-1.1,1.2,0.4,-0.3,0.5,0.04,0.04], time_from_start: {sec:3, nanosec:0} }
  ]
}"
```
