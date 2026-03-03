# ROS2 Camera HTTP Bridge

This bridge exposes a ROS2 camera topic over HTTP so Unity can consume it.

## What it does
- Subscribes to `sensor_msgs/Image`
- Encodes latest frame as JPEG
- Serves latest frame at `http://<host>:8080/frame.jpg`

## Run

```bash
python3 camera_http_bridge.py --topic /camera/color/image_raw --port 8080
```

## Dependencies

- ROS2 + `rclpy`
- `sensor_msgs`
- `cv_bridge`
- OpenCV (`cv2`)

On Ubuntu/ROS2 this is typically:

```bash
sudo apt install ros-$ROS_DISTRO-cv-bridge python3-opencv
```

## Unity side
Use `Assets/Scripts/HttpCameraFeed.cs` in the Unity project and point it to:

```text
http://<ros2-machine-ip>:8080/frame.jpg
```

Set either:
- `targetRenderer` (material texture), or
- `targetRawImage` (UI).

## Notes
- This is a pragmatic first step for teleop/vision prototyping.
- For lower latency later, you can migrate to WebRTC or a native ROS image subscriber in Unity.
