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

## Run (recommended, 3 terminals)

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

### Terminal C: Autonomy bridge bundle (bridge + pose planner + floor)
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_unity_bridge autonomy.launch.py
```

This launch now also starts:
- a TCP waypoint listener on `0.0.0.0:9100`
- it accepts newline-delimited JSON from a Windows GUI
- it republishes received waypoints as `geometry_msgs/PoseStamped` on `/unity/grasp_target`

### Terminal C (pick sequence mode): bridge + staged pick planner + floor
```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_unity_bridge pick_autonomy.launch.py
```

This one launch starts:
- `/unity/grasp_target` staged pick planner (pregrasp -> grasp -> close -> lift)
- Continuous floor collision publisher (so floor doesn't disappear)

Note: In pick mode, the RViz display bridge is intentionally disabled to avoid trajectory conflicts.

Now you only need 3 terminals total.

## Windows coordinate input

If you want to send coordinates from a Windows controller instead of publishing ROS topics directly, send newline-delimited JSON to the Linux machine on port `9100`.

Example:

```json
{"command":"goto_waypoint","frame_id":"world","waypoint":{"name":"Home","x":0.45,"y":0.0,"z":0.35}}
```

Health check:

```json
{"command":"ping"}
```

The TCP listener responds with one JSON line per request.

If you want to run the listener by itself:

```bash
cd ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch ur10e_unity_bridge tcp_waypoint_listener.launch.py
```

## Camera/Perception-driven auto planning (starter)
Publish a target pose to `/unity/grasp_target` (`geometry_msgs/PoseStamped`) and ROS2 will plan automatically,
then send trajectory to Unity.

### Manual test target publish
```bash
source /opt/ros/humble/setup.bash
source ~/EricBerg/Chalmers/Kandidatarbete/ros2_ws/install/setup.bash
ros2 topic pub -1 /unity/grasp_target geometry_msgs/PoseStamped "{
  header: {frame_id: 'world'},
  pose: {
    position: {x: 0.45, y: 0.0, z: 0.35},
    orientation: {x: 0.0, y: 1.0, z: 0.0, w: 0.0}
  }
}"
```

