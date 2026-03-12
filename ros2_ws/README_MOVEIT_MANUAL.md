# UR10e MoveIt (manual config)

## Build
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ur_description ur10e_moveit_config --allow-overriding ur_description
source install/setup.bash
```

## Launch MoveIt demo
```bash
ros2 launch ur10e_moveit_config demo.launch.py
```

Notes:
- Default planning pipeline is OMPL.
- CHOMP is also loaded; switch planner in RViz MotionPlanning panel if available.
- This config is for planning/simulation first (controller execution wiring comes next).
