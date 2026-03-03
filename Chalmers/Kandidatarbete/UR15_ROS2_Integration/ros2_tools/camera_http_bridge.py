#!/usr/bin/env python3
"""
ROS2 camera -> HTTP bridge

Subscribes to sensor_msgs/Image and serves latest frame on:
  - /frame.jpg   (single JPEG)
  - /healthz

Example:
  python3 camera_http_bridge.py --topic /camera/color/image_raw --host 192.168.50.165 --port 18081
"""

import argparse
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class SharedFrame:
    def __init__(self):
        self.lock = threading.Lock()
        self.jpg_bytes = None


class CameraBridgeNode(Node):
    def __init__(self, topic: str, jpeg_quality: int, shared: SharedFrame):
        super().__init__("camera_http_bridge")
        self.bridge = CvBridge()
        self.shared = shared
        self.encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
        self.sub = self.create_subscription(Image, topic, self.on_image, 10)
        self.get_logger().info(f"Subscribed to {topic}")

    def on_image(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
            ok, enc = cv2.imencode('.jpg', frame, self.encode_params)
            if not ok:
                return
            jpg = enc.tobytes()
            with self.shared.lock:
                self.shared.jpg_bytes = jpg
        except Exception as exc:
            self.get_logger().error(f"Failed to process image: {exc}")


class Handler(BaseHTTPRequestHandler):
    shared_frame = None

    def _send_bytes(self, code: int, content_type: str, payload: bytes):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/healthz":
            self._send_bytes(200, "text/plain", b"ok")
            return

        if self.path != "/frame.jpg":
            self._send_bytes(404, "text/plain", b"not found")
            return

        with self.shared_frame.lock:
            jpg = self.shared_frame.jpg_bytes

        if jpg is None:
            self._send_bytes(503, "text/plain", b"no frame yet")
            return

        self._send_bytes(200, "image/jpeg", jpg)

    def log_message(self, fmt, *args):
        return


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--topic", default="/camera/image_raw")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=18081)
    p.add_argument("--jpeg-quality", type=int, default=80)
    return p.parse_args()


def main():
    args = parse_args()
    shared = SharedFrame()

    rclpy.init()
    node = CameraBridgeNode(args.topic, args.jpeg_quality, shared)

    Handler.shared_frame = shared
    server = ThreadingHTTPServer((args.host, args.port), Handler)

    http_thread = threading.Thread(target=server.serve_forever, daemon=True)
    http_thread.start()

    node.get_logger().info(f"HTTP camera available at http://{args.host}:{args.port}/frame.jpg")

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
