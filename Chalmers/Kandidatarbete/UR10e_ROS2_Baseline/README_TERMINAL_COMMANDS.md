# UR10e ROS2 Baseline — Terminal Commands

Use these commands exactly (one command per line).

## A) Start ROS TCP Endpoint (required)
Keep this terminal open while Unity is in Play mode.

```bash
cd ~/unity_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

## B) Verify Unity subscriber is connected
Run this in a second terminal after pressing Play in Unity.

```bash
source /opt/ros/humble/setup.bash
ros2 topic list
ros2 topic info /unity/ur10e_joint_trajectory
```

Expected while Unity Play is active:
- `Subscription count: 1`

## C) Move arm + gripper (quick test)

```bash
source /opt/ros/humble/setup.bash
ros2 topic pub --once /unity/ur10e_joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint','left_finger_joint','right_finger_joint'],
  points: [
    { positions: [0.0, -1.57, 1.57, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 0, nanosec: 0} },
    { positions: [0.7, -1.1, 1.2, 0.4, -0.3, 0.5, 0.04, 0.04], time_from_start: {sec: 3, nanosec: 0} },
    { positions: [0.0, -1.57, 1.57, 0.0, 0.0, 0.0, 0.0, 0.0], time_from_start: {sec: 6, nanosec: 0} }
  ]
}"
```

## D) Finger-only test

```bash
source /opt/ros/humble/setup.bash
ros2 topic pub --once /unity/ur10e_joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['left_finger_joint','right_finger_joint'],
  points: [
    { positions: [0.00, 0.00], time_from_start: {sec: 0, nanosec: 0} },
    { positions: [0.05, 0.05], time_from_start: {sec: 2, nanosec: 0} },
    { positions: [0.00, 0.00], time_from_start: {sec: 4, nanosec: 0} }
  ]
}"
```

## E) Faster / larger motion demo

```bash
source /opt/ros/humble/setup.bash
ros2 topic pub --once /unity/ur10e_joint_trajectory trajectory_msgs/msg/JointTrajectory "{
  joint_names: ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint','left_finger_joint','right_finger_joint'],
  points: [
    { positions: [ 0.00, -1.57, 1.57, 0.00, 0.00, 0.00, 0.00, 0.00 ], time_from_start: {sec: 0, nanosec: 0} },
    { positions: [ 1.40, -0.80, 0.80, 1.20, -1.00, 1.30, 0.06, 0.06 ], time_from_start: {sec: 2, nanosec: 0} },
    { positions: [-1.40, -2.10, 2.20, -1.20, 1.10, -1.30, 0.00, 0.00 ], time_from_start: {sec: 4, nanosec: 0} },
    { positions: [ 0.00, -1.57, 1.57, 0.00, 0.00, 0.00, 0.00, 0.00 ], time_from_start: {sec: 6, nanosec: 0} }
  ]
}"
```

## F) Common errors

### "Unknown topic /unity/ur10e_joint_trajectory"
- Unity not in Play mode, or control script not attached.

### "Waiting for at least 1 matching subscription"
- Endpoint running, but Unity subscriber not active.

### ROS1/ROS2 protocol mismatch
- In Unity: `Robotics -> ROS Settings` and set ROS2.

### Input error (legacy vs Input System)
- Set **Active Input Handling** to **Both** in Player settings.
