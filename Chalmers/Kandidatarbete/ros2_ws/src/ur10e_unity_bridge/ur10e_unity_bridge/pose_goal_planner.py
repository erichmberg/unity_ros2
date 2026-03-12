#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped, Vector3
from shape_msgs.msg import SolidPrimitive
from trajectory_msgs.msg import JointTrajectory

from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest,
    PlanningOptions,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
)


class PoseGoalPlanner(Node):
    def __init__(self):
        super().__init__('pose_goal_planner')

        self.declare_parameter('input_topic', '/unity/grasp_target')
        self.declare_parameter('unity_topic', '/unity/ur10e_joint_trajectory')
        self.declare_parameter('action_name', '/move_action')
        self.declare_parameter('group_name', 'ur10e_arm')
        self.declare_parameter('ee_link', 'wrist_3_link')
        self.declare_parameter('pipeline_id', 'ompl')
        self.declare_parameter('planner_id', 'RRTConnectkConfigDefault')
        self.declare_parameter('allowed_planning_time', 10.0)
        self.declare_parameter('num_planning_attempts', 10)
        self.declare_parameter('max_velocity_scaling_factor', 0.35)
        self.declare_parameter('max_acceleration_scaling_factor', 0.25)
        self.declare_parameter('position_tolerance', 0.02)
        self.declare_parameter('orientation_tolerance', 0.12)

        self.input_topic = self.get_parameter('input_topic').value
        self.unity_topic = self.get_parameter('unity_topic').value
        self.action_name = self.get_parameter('action_name').value
        self.group_name = self.get_parameter('group_name').value
        self.ee_link = self.get_parameter('ee_link').value

        self.pub = self.create_publisher(JointTrajectory, self.unity_topic, 10)
        self.sub = self.create_subscription(PoseStamped, self.input_topic, self.on_target, 10)
        self.client = ActionClient(self, MoveGroup, self.action_name)

        self.busy = False
        self.get_logger().info(f'Listening pose targets on: {self.input_topic}')
        self.get_logger().info(f'MoveGroup action: {self.action_name}')
        self.get_logger().info(f'Publishing trajectories to Unity: {self.unity_topic}')

    def build_goal(self, target: PoseStamped):
        position_tolerance = float(self.get_parameter('position_tolerance').value)
        orientation_tolerance = float(self.get_parameter('orientation_tolerance').value)

        # Position constraint as a small box around target
        primitive = SolidPrimitive()
        primitive.type = SolidPrimitive.BOX
        primitive.dimensions = [position_tolerance * 2.0, position_tolerance * 2.0, position_tolerance * 2.0]

        region = BoundingVolume()
        region.primitives.append(primitive)
        region.primitive_poses.append(target.pose)

        pos_c = PositionConstraint()
        pos_c.header = target.header
        pos_c.link_name = self.ee_link
        pos_c.constraint_region = region
        pos_c.weight = 1.0

        ori_c = OrientationConstraint()
        ori_c.header = target.header
        ori_c.link_name = self.ee_link
        ori_c.orientation = target.pose.orientation
        ori_c.absolute_x_axis_tolerance = orientation_tolerance
        ori_c.absolute_y_axis_tolerance = orientation_tolerance
        ori_c.absolute_z_axis_tolerance = orientation_tolerance
        ori_c.weight = 1.0

        constraints = Constraints()
        constraints.position_constraints.append(pos_c)
        constraints.orientation_constraints.append(ori_c)

        req = MotionPlanRequest()
        req.group_name = self.group_name
        req.pipeline_id = str(self.get_parameter('pipeline_id').value)
        req.planner_id = str(self.get_parameter('planner_id').value)
        req.num_planning_attempts = int(self.get_parameter('num_planning_attempts').value)
        req.allowed_planning_time = float(self.get_parameter('allowed_planning_time').value)
        req.max_velocity_scaling_factor = float(self.get_parameter('max_velocity_scaling_factor').value)
        req.max_acceleration_scaling_factor = float(self.get_parameter('max_acceleration_scaling_factor').value)
        req.goal_constraints.append(constraints)

        opts = PlanningOptions()
        opts.plan_only = True
        opts.look_around = False
        opts.replan = False

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = opts
        return goal

    def on_target(self, msg: PoseStamped):
        if self.busy:
            self.get_logger().warn('Planner busy, dropping target')
            return

        if not self.client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error('move_action server not available')
            return

        self.busy = True
        goal = self.build_goal(msg)
        self.get_logger().info(
            f'Planning to target in frame={msg.header.frame_id}: '
            f'[{msg.pose.position.x:.3f}, {msg.pose.position.y:.3f}, {msg.pose.position.z:.3f}]'
        )
        future = self.client.send_goal_async(goal)
        future.add_done_callback(self.on_goal_response)

    def on_goal_response(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('MoveGroup goal rejected')
            self.busy = False
            return
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.on_result)

    def on_result(self, future):
        try:
            result = future.result().result
            traj = result.planned_trajectory.joint_trajectory
            if traj.joint_names and traj.points:
                self.pub.publish(traj)
                self.get_logger().info(
                    f'Published planned trajectory to Unity: joints={len(traj.joint_names)} points={len(traj.points)}'
                )
            else:
                self.get_logger().warn('Planning returned empty trajectory')
        except Exception as e:
            self.get_logger().error(f'Planning failed: {e}')
        finally:
            self.busy = False


def main():
    rclpy.init()
    node = PoseGoalPlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
