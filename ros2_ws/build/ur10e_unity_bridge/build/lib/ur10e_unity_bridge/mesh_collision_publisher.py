#!/usr/bin/env python3
import os
import struct
import rclpy
from rclpy.node import Node
from moveit_msgs.msg import CollisionObject
from shape_msgs.msg import Mesh, MeshTriangle
from geometry_msgs.msg import Pose, Point


def _read_stl(path: str):
    with open(path, 'rb') as f:
        header = f.read(80)
        tri_count_raw = f.read(4)
        if len(tri_count_raw) != 4:
            raise RuntimeError('Invalid STL: missing triangle count')
        tri_count = struct.unpack('<I', tri_count_raw)[0]
        expected = 84 + tri_count * 50
        f.seek(0, os.SEEK_END)
        size = f.tell()

    if size == expected:
        return _read_stl_binary(path, tri_count)
    return _read_stl_ascii(path)


def _read_stl_binary(path: str, tri_count: int):
    vertices = []
    triangles = []

    with open(path, 'rb') as f:
        f.seek(84)
        for _ in range(tri_count):
            rec = f.read(50)
            if len(rec) != 50:
                break
            # skip normal (12 bytes)
            v = struct.unpack('<12fH', rec)
            p0 = (v[3], v[4], v[5])
            p1 = (v[6], v[7], v[8])
            p2 = (v[9], v[10], v[11])
            i0 = len(vertices); vertices.append(p0)
            i1 = len(vertices); vertices.append(p1)
            i2 = len(vertices); vertices.append(p2)
            triangles.append((i0, i1, i2))

    return vertices, triangles


def _read_stl_ascii(path: str):
    vertices = []
    triangles = []

    tri = []
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if s.startswith('vertex '):
                parts = s.split()
                if len(parts) >= 4:
                    tri.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif s.startswith('endfacet'):
                if len(tri) >= 3:
                    p0, p1, p2 = tri[-3], tri[-2], tri[-1]
                    i0 = len(vertices); vertices.append(p0)
                    i1 = len(vertices); vertices.append(p1)
                    i2 = len(vertices); vertices.append(p2)
                    triangles.append((i0, i1, i2))
                tri = []

    return vertices, triangles


class MeshCollisionPublisher(Node):
    def __init__(self):
        super().__init__('mesh_collision_publisher')

        self.declare_parameter('topic', '/collision_object')
        self.declare_parameter('frame_id', 'world')
        self.declare_parameter('id', 'rita_cell_mesh')
        self.declare_parameter('mesh_path', '~/EricBerg/Chalmers/Kandidatarbete/UR10e_ROS2_Baseline/Assets/Environment/RITA CELL.stl')
        self.declare_parameter('scale', 1.0)
        self.declare_parameter('x', 0.0)
        self.declare_parameter('y', 0.0)
        self.declare_parameter('z', 0.0)
        self.declare_parameter('qx', 0.0)
        self.declare_parameter('qy', 0.0)
        self.declare_parameter('qz', 0.0)
        self.declare_parameter('qw', 1.0)
        self.declare_parameter('repeats', 8)
        self.declare_parameter('period_s', 0.5)

        topic = self.get_parameter('topic').value
        self.frame_id = self.get_parameter('frame_id').value
        self.obj_id = self.get_parameter('id').value
        self.mesh_path = os.path.expanduser(str(self.get_parameter('mesh_path').value))
        self.scale = float(self.get_parameter('scale').value)
        self.repeats = int(self.get_parameter('repeats').value)
        self.period_s = float(self.get_parameter('period_s').value)

        self.pose = Pose()
        self.pose.position.x = float(self.get_parameter('x').value)
        self.pose.position.y = float(self.get_parameter('y').value)
        self.pose.position.z = float(self.get_parameter('z').value)
        self.pose.orientation.x = float(self.get_parameter('qx').value)
        self.pose.orientation.y = float(self.get_parameter('qy').value)
        self.pose.orientation.z = float(self.get_parameter('qz').value)
        self.pose.orientation.w = float(self.get_parameter('qw').value)

        self.pub = self.create_publisher(CollisionObject, topic, 10)
        self.count = 0

        if not os.path.exists(self.mesh_path):
            self.get_logger().error(f'Mesh not found: {self.mesh_path}')
            return

        try:
            verts, tris = _read_stl(self.mesh_path)
        except Exception as e:
            self.get_logger().error(f'Failed to parse STL: {e}')
            return

        mesh = Mesh()
        for a, b, c in tris:
            t = MeshTriangle()
            t.vertex_indices = [int(a), int(b), int(c)]
            mesh.triangles.append(t)

        s = self.scale
        for x, y, z in verts:
            p = Point()
            p.x = float(x) * s
            p.y = float(y) * s
            p.z = float(z) * s
            mesh.vertices.append(p)

        self.msg = CollisionObject()
        self.msg.header.frame_id = self.frame_id
        self.msg.id = self.obj_id
        self.msg.operation = CollisionObject.ADD
        self.msg.meshes.append(mesh)
        self.msg.mesh_poses.append(self.pose)

        self.get_logger().info(
            f'Loaded mesh {self.mesh_path} ' 
            f'(verts={len(mesh.vertices)}, tris={len(mesh.triangles)})'
        )

        self.timer = self.create_timer(self.period_s, self.publish_once)

    def publish_once(self):
        if not hasattr(self, 'msg'):
            return
        self.pub.publish(self.msg)
        self.count += 1
        if self.repeats > 0 and self.count >= self.repeats:
            self.get_logger().info('Mesh collision object published.')
            self.timer.cancel()


def main():
    rclpy.init()
    node = MeshCollisionPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
