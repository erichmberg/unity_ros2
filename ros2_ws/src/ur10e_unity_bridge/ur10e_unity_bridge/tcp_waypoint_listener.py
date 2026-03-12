#!/usr/bin/env python3
import json
import queue
import socketserver
import threading

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node


class QueuedRequest:
    def __init__(self, payload, client_address):
        self.payload = payload
        self.client_address = client_address
        self.response = {
            "ok": False,
            "message": "Request was not handled.",
        }
        self.event = threading.Event()


class WaypointRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            line = self.rfile.readline()

            if not line:
                break

            try:
                payload = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                self.wfile.write((json.dumps({
                    "ok": False,
                    "message": "Invalid JSON request.",
                }) + "\n").encode("utf-8"))
                continue

            request = QueuedRequest(payload, self.client_address)
            self.server.node.request_queue.put(request)

            if not request.event.wait(timeout=5.0):
                self.wfile.write((json.dumps({
                    "ok": False,
                    "message": "Timed out waiting for ROS 2 processing.",
                }) + "\n").encode("utf-8"))
                continue

            self.wfile.write((json.dumps(request.response) + "\n").encode("utf-8"))


class ThreadedWaypointServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, request_handler_class, node):
        super().__init__(server_address, request_handler_class)
        self.node = node


class TcpWaypointListener(Node):
    def __init__(self):
        super().__init__("tcp_waypoint_listener")

        self.declare_parameter("bind_host", "0.0.0.0")
        self.declare_parameter("bind_port", 9100)
        self.declare_parameter("output_topic", "/unity/grasp_target")
        self.declare_parameter("frame_id", "world")

        self.bind_host = str(self.get_parameter("bind_host").value)
        self.bind_port = int(self.get_parameter("bind_port").value)
        self.output_topic = str(self.get_parameter("output_topic").value)
        self.default_frame_id = str(self.get_parameter("frame_id").value)

        self.publisher = self.create_publisher(PoseStamped, self.output_topic, 10)
        self.request_queue = queue.Queue()
        self.create_timer(0.05, self._process_requests)

        self.server = ThreadedWaypointServer((self.bind_host, self.bind_port), WaypointRequestHandler, self)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()

        self.get_logger().info(
            f"TCP waypoint listener active on {self.bind_host}:{self.bind_port}, publishing to {self.output_topic}"
        )

    def destroy_node(self):
        self.server.shutdown()
        self.server.server_close()
        super().destroy_node()

    def _process_requests(self):
        while True:
            try:
                request = self.request_queue.get_nowait()
            except queue.Empty:
                return

            request.response = self._handle_request(request.payload, request.client_address)
            request.event.set()

    def _handle_request(self, payload, client_address):
        command = str(payload.get("command", "")).strip().lower()

        if command == "ping":
            self.get_logger().info(f"Ping received from {client_address[0]}:{client_address[1]}")
            return {
                "ok": True,
                "message": "ROS 2 waypoint listener is alive.",
            }

        if command != "goto_waypoint":
            return {
                "ok": False,
                "message": f"Unknown command '{payload.get('command', '')}'.",
            }

        waypoint = payload.get("waypoint") or {}
        waypoint_name = str(waypoint.get("name", "Unnamed")).strip() or "Unnamed"
        frame_id = str(payload.get("frame_id", self.default_frame_id)).strip() or self.default_frame_id

        try:
            x = float(waypoint["x"])
            y = float(waypoint["y"])
            z = float(waypoint["z"])
        except (KeyError, TypeError, ValueError):
            return {
                "ok": False,
                "message": "Waypoint payload must contain numeric x, y, and z values.",
            }

        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = frame_id
        pose.pose.position.x = x
        pose.pose.position.y = y
        pose.pose.position.z = z
        pose.pose.orientation.w = 1.0

        self.publisher.publish(pose)
        self.get_logger().info(
            f"Received waypoint '{waypoint_name}' from {client_address[0]}:{client_address[1]} "
            f"in frame '{frame_id}': x={x:.3f} y={y:.3f} z={z:.3f}"
        )

        return {
            "ok": True,
            "message": f"Accepted waypoint '{waypoint_name}'.",
            "topic": self.output_topic,
            "frame_id": frame_id,
        }


def main():
    rclpy.init()
    node = TcpWaypointListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
