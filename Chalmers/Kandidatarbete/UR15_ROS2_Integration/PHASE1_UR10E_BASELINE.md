# Phase 1 — UR10e Unity Baseline (Clean)

This baseline removes earlier test/debug scripts and keeps ROS2 Humble trajectory control for UR10e.

## Kept
- `Assets/robot/ur10e_official.urdf`
- `Assets/Scripts/JointTrajectoryToUr10e.cs`
- `Assets/Scripts/AutoAnchorArticulationRoots.cs` (prevents robot tipping)

## Removed (old test/debug)
- Gripper keyboard test script
- Legacy joint-state test script
- Unity HTTP camera stream scripts
- Legacy UR15 trajectory script name and dual-topic behavior
- Drive auto-config script

## ROS2 topic
- `/unity/ur10e_joint_trajectory`

## Terminal commands

### 1) ROS TCP endpoint
```bash
cd ~/unity_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

### 2) Quick trajectory test
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
