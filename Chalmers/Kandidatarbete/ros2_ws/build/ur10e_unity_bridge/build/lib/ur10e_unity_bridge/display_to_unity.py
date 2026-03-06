#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.msg import DisplayTrajectory
from trajectory_msgs.msg import JointTrajectory


class DisplayToUnityBridge(Node):
    def __init__(self):
        super().__init__('display_to_unity_bridge')
        self.declare_parameter('input_topic', '/display_planned_path')
        self.declare_parameter('unity_topic', '/unity/ur10e_joint_trajectory')
        self.declare_parameter('publish_on_every_plan', True)

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        unity_topic = self.get_parameter('unity_topic').get_parameter_value().string_value
        self.publish_on_every_plan = self.get_parameter('publish_on_every_plan').get_parameter_value().bool_value

        self.pub = self.create_publisher(JointTrajectory, unity_topic, 10)
        self.sub = self.create_subscription(DisplayTrajectory, input_topic, self.cb, 10)

        self.get_logger().info(f'Listening: {input_topic}')
        self.get_logger().info(f'Publishing to Unity: {unity_topic}')

    def cb(self, msg: DisplayTrajectory):
        if not self.publish_on_every_plan:
            return
        if not msg.trajectory:
            self.get_logger().warn('DisplayTrajectory received but no trajectory entries')
            return

        # Use latest trajectory and latest multi_dof entry not needed for Unity
        robot_traj = msg.trajectory[-1]
        jt = robot_traj.joint_trajectory
        if not jt.joint_names or not jt.points:
            self.get_logger().warn('Joint trajectory empty, skipping')
            return

        out = JointTrajectory()
        out.header = jt.header
        out.joint_names = list(jt.joint_names)
        out.points = list(jt.points)

        self.pub.publish(out)
        self.get_logger().info(
            f'Published trajectory to Unity: joints={len(out.joint_names)} points={len(out.points)}'
        )


def main():
    rclpy.init()
    node = DisplayToUnityBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
