#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest,
    PlanningOptions,
    Constraints,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
)
from shape_msgs.msg import SolidPrimitive


class PickSequencePlanner(Node):
    def __init__(self):
        super().__init__('pick_sequence_planner')

        # IO
        self.declare_parameter('input_topic', '/unity/grasp_target')
        self.declare_parameter('unity_topic', '/unity/ur10e_joint_trajectory')
        self.declare_parameter('action_name', '/move_action')

        # Planning
        self.declare_parameter('group_name', 'ur10e_arm')
        self.declare_parameter('ee_link', 'gripper_base_link')
        self.declare_parameter('pipeline_id', 'ompl')
        self.declare_parameter('planner_id', 'RRTConnectkConfigDefault')
        self.declare_parameter('allowed_planning_time', 15.0)
        self.declare_parameter('num_planning_attempts', 20)
        self.declare_parameter('max_velocity_scaling_factor', 0.2)
        self.declare_parameter('max_acceleration_scaling_factor', 0.2)
        self.declare_parameter('position_tolerance', 0.02)
        self.declare_parameter('orientation_tolerance', 3.14)

        # Grasp geometry / sequence
        self.declare_parameter('grasp_offset_x', 0.0)
        self.declare_parameter('grasp_offset_y', 0.0)
        self.declare_parameter('grasp_offset_z', 0.06)
        self.declare_parameter('pregrasp_lift', 0.10)
        self.declare_parameter('postgrasp_lift', 0.12)
        self.declare_parameter('close_width', 0.04)
        self.declare_parameter('gripper_close_seconds', 1.0)
        self.declare_parameter('stage_settle_seconds', 0.4)

        self.input_topic = self.get_parameter('input_topic').value
        self.unity_topic = self.get_parameter('unity_topic').value
        self.group_name = self.get_parameter('group_name').value
        self.ee_link = self.get_parameter('ee_link').value

        self.pub = self.create_publisher(JointTrajectory, self.unity_topic, 10)
        self.sub = self.create_subscription(PoseStamped, self.input_topic, self.on_target, 10)
        self.client = ActionClient(self, MoveGroup, self.get_parameter('action_name').value)

        self.busy = False
        self.base_target = None
        self._stage_timer = None

        self.get_logger().info('PickSequencePlanner ready')
        self.get_logger().info(f'Listening targets: {self.input_topic}')
        self.get_logger().info(f'Publishing to Unity: {self.unity_topic}')

    def on_target(self, msg: PoseStamped):
        if self.busy:
            self.get_logger().warn('Busy with previous pick sequence, dropping target')
            return

        if not self.client.wait_for_server(timeout_sec=1.0):
            self.get_logger().error('move_action server not available')
            return

        self.busy = True
        self.base_target = msg
        self.get_logger().info(
            f'Pick sequence start for target: '
            f'[{msg.pose.position.x:.3f}, {msg.pose.position.y:.3f}, {msg.pose.position.z:.3f}]'
        )

        pre = self._make_adjusted_pose(msg, z_extra=float(self.get_parameter('pregrasp_lift').value))
        self._plan_and_publish(pre, self._after_pregrasp)

    def _make_adjusted_pose(self, src: PoseStamped, z_extra: float = 0.0):
        p = PoseStamped()
        p.header = src.header
        p.pose = src.pose
        p.pose.position.x += float(self.get_parameter('grasp_offset_x').value)
        p.pose.position.y += float(self.get_parameter('grasp_offset_y').value)
        p.pose.position.z += float(self.get_parameter('grasp_offset_z').value) + z_extra
        return p

    def _build_goal(self, target: PoseStamped):
        position_tolerance = float(self.get_parameter('position_tolerance').value)
        orientation_tolerance = float(self.get_parameter('orientation_tolerance').value)

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

        goal = MoveGroup.Goal()
        goal.request = req
        goal.planning_options = opts
        return goal

    def _plan_and_publish(self, target: PoseStamped, next_cb):
        goal = self._build_goal(target)
        self.get_logger().info(
            f'Planning stage pose: [{target.pose.position.x:.3f}, {target.pose.position.y:.3f}, {target.pose.position.z:.3f}]'
        )
        future = self.client.send_goal_async(goal)

        def on_goal_response(fut):
            gh = fut.result()
            if not gh.accepted:
                self.get_logger().error('Goal rejected')
                self.busy = False
                return
            rf = gh.get_result_async()

            def on_result(done_fut):
                try:
                    result = done_fut.result().result
                    traj = result.planned_trajectory.joint_trajectory
                    if not traj.joint_names or not traj.points:
                        self.get_logger().warn('Planning returned empty trajectory')
                        self.busy = False
                        return
                    self.pub.publish(traj)
                    dur = self._traj_duration(traj) + float(self.get_parameter('stage_settle_seconds').value)
                    self.get_logger().info(f'Published stage trajectory, waiting {dur:.2f}s')
                    self._set_stage_timer(max(0.1, dur), next_cb)
                except Exception as e:
                    self.get_logger().error(f'Planning failed: {e}')
                    self.busy = False

            rf.add_done_callback(on_result)

        future.add_done_callback(on_goal_response)

    @staticmethod
    def _traj_duration(traj: JointTrajectory):
        if not traj.points:
            return 0.0
        d = traj.points[-1].time_from_start
        return float(d.sec) + float(d.nanosec) * 1e-9

    def _after_pregrasp(self):
        self._cancel_timer_callbacks()
        grasp = self._make_adjusted_pose(self.base_target, z_extra=0.0)
        self._plan_and_publish(grasp, self._after_grasp)

    def _after_grasp(self):
        self._cancel_timer_callbacks()
        self._publish_gripper_close()
        wait_s = float(self.get_parameter('gripper_close_seconds').value) + float(self.get_parameter('stage_settle_seconds').value)
        self._set_stage_timer(wait_s, self._after_close)

    def _after_close(self):
        self._cancel_timer_callbacks()
        lift = self._make_adjusted_pose(self.base_target, z_extra=float(self.get_parameter('postgrasp_lift').value))
        self._plan_and_publish(lift, self._finish)

    def _finish(self):
        self._cancel_timer_callbacks()
        self.get_logger().info('Pick sequence complete')
        self.busy = False

    def _publish_gripper_close(self):
        width = float(self.get_parameter('close_width').value)
        t = float(self.get_parameter('gripper_close_seconds').value)

        traj = JointTrajectory()
        traj.joint_names = ['left_finger_joint', 'right_finger_joint']

        p0 = JointTrajectoryPoint()
        p0.positions = [0.0, 0.0]
        p0.time_from_start.sec = 0
        p0.time_from_start.nanosec = 0

        p1 = JointTrajectoryPoint()
        p1.positions = [width, width]
        sec = int(math.floor(t))
        nsec = int((t - sec) * 1e9)
        p1.time_from_start.sec = sec
        p1.time_from_start.nanosec = nsec

        traj.points = [p0, p1]
        self.pub.publish(traj)
        self.get_logger().info(f'Published gripper close trajectory to width {width:.3f}m')

    def _set_stage_timer(self, seconds, cb):
        self._cancel_timer_callbacks()

        def _wrapped():
            if self._stage_timer is not None and not self._stage_timer.is_canceled():
                self._stage_timer.cancel()
            self._stage_timer = None
            cb()

        self._stage_timer = self.create_timer(seconds, _wrapped)

    def _cancel_timer_callbacks(self):
        if self._stage_timer is not None and not self._stage_timer.is_canceled():
            self._stage_timer.cancel()
        self._stage_timer = None


def main():
    rclpy.init()
    node = PickSequencePlanner()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
