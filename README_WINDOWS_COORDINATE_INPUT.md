# Windows Coordinate Input Integration

This note explains what must change in this repo so a Windows computer can send waypoint coordinates to the Linux ROS 2 side.

## What already exists

This repo already has the planning path you want after a pose reaches ROS 2:

- [ros2_ws/src/ur10e_unity_bridge/ur10e_unity_bridge/pose_goal_planner.py](/C:/Users/Student/OneDrive%20-%20Chalmers/Desktop/Kandidat2026%20COBOT/unity_ros2/ros2_ws/src/ur10e_unity_bridge/ur10e_unity_bridge/pose_goal_planner.py)
  subscribes to `/unity/grasp_target` as `geometry_msgs/PoseStamped`
- it sends that pose to MoveIt through the `MoveGroup` action
- when planning succeeds, it republishes the resulting `JointTrajectory` to `/unity/ur10e_joint_trajectory`
- Unity already subscribes to `/unity/ur10e_joint_trajectory`

That means:

- do not replace `pose_goal_planner.py`
- feed it better

## The missing piece

The repo does **not** currently contain a plain TCP listener for an external Windows GUI.

Right now the expected input path is either:

- Unity publishing `/unity/grasp_target` through ROS TCP Connector
- or manual `ros2 topic pub`

Your Windows coordinate GUI is neither of those.

So the missing piece is a small ROS 2 node that:

1. listens on a TCP port on Linux
2. receives newline-delimited JSON from Windows
3. converts that JSON into `geometry_msgs/PoseStamped`
4. publishes it to `/unity/grasp_target`

Once that happens, the rest of this repo can stay mostly unchanged.

## Recommended design

Add a new node to the `ur10e_unity_bridge` package.

Recommended file:

- `ros2_ws/src/ur10e_unity_bridge/ur10e_unity_bridge/tcp_waypoint_listener.py`

Responsibilities:

- open a TCP server on `0.0.0.0:9100`
- accept `ping`
- accept `goto_waypoint`
- publish `PoseStamped` on `/unity/grasp_target`
- reply with one-line JSON acknowledgements

## Required protocol

The Windows machine sends one JSON object per line.

Example request:

```json
{
  "command": "goto_waypoint",
  "frame_id": "world",
  "waypoint": {
    "name": "Home",
    "x": 0.45,
    "y": 0.0,
    "z": 0.35
  }
}
```

Example success response:

```json
{"ok":true,"message":"Accepted waypoint 'Home'."}
```

Example ping:

```json
{"command":"ping"}
```

Example ping response:

```json
{"ok":true,"message":"ROS 2 waypoint listener is alive."}
```

## Files that should change

### 1. Add a new Python node

Add:

- `ros2_ws/src/ur10e_unity_bridge/ur10e_unity_bridge/tcp_waypoint_listener.py`

It should:

- create a ROS 2 publisher for `geometry_msgs/PoseStamped`
- publish to `/unity/grasp_target`
- use a thread-safe queue between the socket thread and ROS 2 thread
- not block the ROS 2 executor

### 2. Register the new node in `setup.py`

Modify:

- [ros2_ws/src/ur10e_unity_bridge/setup.py](/C:/Users/Student/OneDrive%20-%20Chalmers/Desktop/Kandidat2026%20COBOT/unity_ros2/ros2_ws/src/ur10e_unity_bridge/setup.py)

Add a new console entry point:

```python
'tcp_waypoint_listener = ur10e_unity_bridge.tcp_waypoint_listener:main',
```

### 3. Optionally add a launch file

Either:

- add a new launch file `tcp_waypoint_listener.launch.py`

or:

- extend [ros2_ws/src/ur10e_unity_bridge/launch/autonomy.launch.py](/C:/Users/Student/OneDrive%20-%20Chalmers/Desktop/Kandidat2026%20COBOT/unity_ros2/ros2_ws/src/ur10e_unity_bridge/launch/autonomy.launch.py)

Recommended parameters:

- `bind_host`: `0.0.0.0`
- `bind_port`: `9100`
- `output_topic`: `/unity/grasp_target`
- `frame_id`: `world`

### 4. Update the docs

Update:

- [ros2_ws/README_UNITY_BRIDGE.md](/C:/Users/Student/OneDrive%20-%20Chalmers/Desktop/Kandidat2026%20COBOT/unity_ros2/ros2_ws/README_UNITY_BRIDGE.md)

Add a section describing:

- starting the TCP listener
- the Windows JSON format
- the default port `9100`

## What should not change

Do not rewrite:

- `pose_goal_planner.py`
- `display_to_unity.py`
- Unity trajectory subscriber logic

Those are already the downstream path.

The new node should only inject goals into:

- `/unity/grasp_target`

## Current network assumption that should be revisited

The existing docs start the ROS TCP endpoint like this:

```bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=127.0.0.1 -p ROS_TCP_PORT:=10000
```

That is only correct if Unity runs on the same Linux machine.

If Unity runs on Windows and must connect across the network, this should be changed to the Linux machine IP or a reachable bind address.

For example:

```bash
ros2 run ros_tcp_endpoint default_server_endpoint --ros-args -p ROS_IP:=192.168.0.50 -p ROS_TCP_PORT:=10000
```

or whatever the Linux machine IP actually is.

This is separate from the new waypoint listener:

- ROS TCP endpoint is for Unity ROS messages
- TCP waypoint listener is for the custom Windows coordinate GUI

## Best implementation path

The cleanest architecture is:

1. Windows GUI sends JSON to Linux on port `9100`
2. `tcp_waypoint_listener.py` publishes `PoseStamped` to `/unity/grasp_target`
3. `pose_goal_planner.py` receives that pose and asks MoveIt to plan
4. planned `JointTrajectory` goes to `/unity/ur10e_joint_trajectory`
5. Unity visualizes / executes the motion

## Minimal acceptance test

After implementation:

1. build the workspace
2. start MoveIt demo
3. start `pose_goal_planner`
4. start `tcp_waypoint_listener`
5. from Windows, send:

```json
{"command":"goto_waypoint","frame_id":"world","waypoint":{"name":"Home","x":0.45,"y":0.0,"z":0.35}}
```

6. confirm the listener publishes `/unity/grasp_target`
7. confirm `pose_goal_planner` logs a planning attempt
8. confirm Unity receives a joint trajectory

## Short implementation summary

To make this repo receive coordinates from the Windows computer, the main change is:

- add one new ROS 2 TCP listener node that publishes `PoseStamped` to `/unity/grasp_target`

Everything else is already mostly present.
