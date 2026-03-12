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
        self.declare_parameter('publish_only_new_trajectory', True)

        input_topic = self.get_parameter('input_topic').get_parameter_value().string_value
        unity_topic = self.get_parameter('unity_topic').get_parameter_value().string_value
        self.publish_on_every_plan = self.get_parameter('publish_on_every_plan').get_parameter_value().bool_value
        self.publish_only_new_trajectory = self.get_parameter('publish_only_new_trajectory').get_parameter_value().bool_value
        self.last_signature = None

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

        # Build a simple signature so stale/repeated plans are not re-published.
        first = jt.points[0]
        last = jt.points[-1]
        signature = (
            tuple(jt.joint_names),
            len(jt.points),
            tuple(round(p, 6) for p in first.positions),
            tuple(round(p, 6) for p in last.positions),
            int(last.time_from_start.sec),
            int(last.time_from_start.nanosec),
        )

        if self.publish_only_new_trajectory and signature == self.last_signature:
            self.get_logger().info('Skipping repeated trajectory (same signature as last publish)')
            return

        out = JointTrajectory()
        out.header = jt.header
        out.joint_names = list(jt.joint_names)
        out.points = list(jt.points)

        self.pub.publish(out)
        self.last_signature = signature
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
