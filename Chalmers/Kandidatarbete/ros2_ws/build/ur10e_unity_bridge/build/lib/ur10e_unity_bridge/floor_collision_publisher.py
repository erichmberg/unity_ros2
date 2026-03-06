#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class FloorCollisionPublisher(Node):
    def __init__(self):
        super().__init__('floor_collision_publisher')
        self.declare_parameter('topic', '/collision_object')
        self.declare_parameter('frame_id', 'world')
        self.declare_parameter('id', 'floor')
        self.declare_parameter('size_x', 4.0)
        self.declare_parameter('size_y', 4.0)
        self.declare_parameter('size_z', 0.10)
        self.declare_parameter('z_center', -0.12)
        self.declare_parameter('repeats', 10)

        topic = self.get_parameter('topic').value
        self.frame_id = self.get_parameter('frame_id').value
        self.obj_id = self.get_parameter('id').value
        self.size_x = float(self.get_parameter('size_x').value)
        self.size_y = float(self.get_parameter('size_y').value)
        self.size_z = float(self.get_parameter('size_z').value)
        self.z_center = float(self.get_parameter('z_center').value)
        self.repeats = int(self.get_parameter('repeats').value)

        self.pub = self.create_publisher(CollisionObject, topic, 10)
        self.count = 0
        self.timer = self.create_timer(0.5, self.publish_once)
        self.get_logger().info(f'Publishing floor collision object to {topic}')

    def publish_once(self):
        msg = CollisionObject()
        msg.header.frame_id = self.frame_id
        msg.id = self.obj_id
        msg.operation = CollisionObject.ADD

        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [self.size_x, self.size_y, self.size_z]

        pose = Pose()
        pose.position.x = 0.0
        pose.position.y = 0.0
        pose.position.z = self.z_center
        pose.orientation.w = 1.0

        msg.primitives.append(primitive)
        msg.primitive_poses.append(pose)

        self.pub.publish(msg)
        self.count += 1

        if self.count >= self.repeats:
            self.get_logger().info('Floor collision object published.')
            self.timer.cancel()


def main():
    rclpy.init()
    node = FloorCollisionPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
