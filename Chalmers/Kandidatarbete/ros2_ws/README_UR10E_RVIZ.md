# UR10e RViz quick start

```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select ur_description
source install/setup.bash
ros2 launch ur_description display.launch.py
```
