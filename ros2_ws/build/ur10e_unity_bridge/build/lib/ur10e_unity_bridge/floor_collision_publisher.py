#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class EnvironmentCollisionPublisher(Node):
    def __init__(self):
        super().__init__('environment_collision_publisher')
        self.declare_parameter('topic', '/collision_object')
        self.declare_parameter('frame_id', 'world')

        # Publish timing
        self.declare_parameter('repeats', 6)
        self.declare_parameter('period_s', 0.5)

        # Floor
        self.declare_parameter('publish_floor', True)
        self.declare_parameter('floor_id', 'floor')
        self.declare_parameter('floor_size_x', 5.0)
        self.declare_parameter('floor_size_y', 5.0)
        self.declare_parameter('floor_size_z', 0.10)
        self.declare_parameter('floor_x', 0.0)
        self.declare_parameter('floor_y', 0.0)
        self.declare_parameter('floor_z', -0.12)

        # Rail beam (critical so planner does not cut through rail)
        self.declare_parameter('publish_rail', True)
        self.declare_parameter('rail_id', 'rail_beam')
        self.declare_parameter('rail_size_x', 4.65)
        self.declare_parameter('rail_size_y', 0.08)
        self.declare_parameter('rail_size_z', 0.08)
        self.declare_parameter('rail_x', 0.0)
        self.declare_parameter('rail_y', -0.02)
        self.declare_parameter('rail_z', 1.6)

        # Optional coarse cell collision approximation (kept off by default)
        self.declare_parameter('publish_cell_box', False)
        self.declare_parameter('cell_id', 'rita_cell_box')
        self.declare_parameter('cell_size_x', 3.0)
        self.declare_parameter('cell_size_y', 3.0)
        self.declare_parameter('cell_size_z', 2.2)
        self.declare_parameter('cell_x', 0.0)
        self.declare_parameter('cell_y', 0.0)
        self.declare_parameter('cell_z', 1.1)

        topic = self.get_parameter('topic').value
        self.frame_id = self.get_parameter('frame_id').value
        self.repeats = int(self.get_parameter('repeats').value)
        self.period_s = float(self.get_parameter('period_s').value)

        self.pub = self.create_publisher(CollisionObject, topic, 10)
        self.count = 0
        self.timer = self.create_timer(self.period_s, self.publish_all)

        self.get_logger().info(
            f'Publishing environment collision objects to {topic} '
            f'(frame={self.frame_id}, repeats={self.repeats})'
        )

    def _publish_box(self, obj_id: str, sx: float, sy: float, sz: float, x: float, y: float, z: float):
        msg = CollisionObject()
        msg.header.frame_id = self.frame_id
        msg.id = obj_id
        msg.operation = CollisionObject.ADD

        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [float(sx), float(sy), float(sz)]

        pose = Pose()
        pose.position.x = float(x)
        pose.position.y = float(y)
        pose.position.z = float(z)
        pose.orientation.w = 1.0

        msg.primitives.append(primitive)
        msg.primitive_poses.append(pose)
        self.pub.publish(msg)

    def publish_all(self):
        if bool(self.get_parameter('publish_floor').value):
            self._publish_box(
                str(self.get_parameter('floor_id').value),
                self.get_parameter('floor_size_x').value,
                self.get_parameter('floor_size_y').value,
                self.get_parameter('floor_size_z').value,
                self.get_parameter('floor_x').value,
                self.get_parameter('floor_y').value,
                self.get_parameter('floor_z').value,
            )

        if bool(self.get_parameter('publish_rail').value):
            self._publish_box(
                str(self.get_parameter('rail_id').value),
                self.get_parameter('rail_size_x').value,
                self.get_parameter('rail_size_y').value,
                self.get_parameter('rail_size_z').value,
                self.get_parameter('rail_x').value,
                self.get_parameter('rail_y').value,
                self.get_parameter('rail_z').value,
            )

        if bool(self.get_parameter('publish_cell_box').value):
            self._publish_box(
                str(self.get_parameter('cell_id').value),
                self.get_parameter('cell_size_x').value,
                self.get_parameter('cell_size_y').value,
                self.get_parameter('cell_size_z').value,
                self.get_parameter('cell_x').value,
                self.get_parameter('cell_y').value,
                self.get_parameter('cell_z').value,
            )

        self.count += 1
        if self.repeats > 0 and self.count >= self.repeats:
            self.get_logger().info('Environment collision objects published.')
            self.timer.cancel()


def main():
    rclpy.init()
    node = EnvironmentCollisionPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
