# UR10e Unity + ROS2 (Public Export)

This repository contains only the candidate thesis simulation stack:

- `UR10e_ROS2_Baseline/` → Unity project
- `ros2_ws/` → ROS2 workspace (MoveIt + bridge + descriptions)

## Project purpose

Simulate a UR10e robot with gripper on a rail, plan motion in MoveIt (RViz), and execute in Unity via ROS-TCP.

---

## Repo structure

```text
.
├── UR10e_ROS2_Baseline/
└── ros2_ws/
```

---

## Requirements

- Ubuntu 22.04
- ROS2 Humble
- Unity (same version used in project)
- Unity ROS-TCP-Connector setup (endpoint package in `~/unity_ros2_ws`)

---

## Quick start

### 1) Build ROS workspace

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ur_description ur10e_moveit_config ur10e_unity_bridge --allow-overriding ur_description
source install/setup.bash
```

### 2) Start ROS-TCP endpoint (Terminal A)

```bash
cd ~/unity_ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

### 3) Start MoveIt + RViz (Terminal B)

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_moveit_config demo.launch.py
```

### 4) Start Unity bridge (Terminal C)

```bash
cd ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_unity_bridge bridge.launch.py
```

### 5) In Unity

- Open `UR10e_ROS2_Baseline`
- Press Play
- Plan in RViz → robot should move in Unity

---

## Notes

- Current stable planner path is OMPL-based RViz planning + `bridge.launch.py`.
- Rail and environment collision behavior are tuned for this project setup.
- If planning fails unexpectedly, restart all 3 terminals and Unity Play mode.

---

## Disclaimer

This is a research/candidate-thesis simulation project.  
Configuration is optimized for our lab/demo environment and may require adjustments on other systems.
