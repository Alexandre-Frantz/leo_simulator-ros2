#!/usr/bin/env python3
"""
lander_rviz_marker.py

Publishes the Argonaut lander STL as a visualization_msgs/Marker (MESH_RESOURCE)
so it can be shown in RViz without a URDF. The marker is stamped in the `lander`
frame and re-published on a latched (transient_local) topic so RViz picks it up
even if it subscribes late.

Run (no build needed):
    python3 lander_rviz_marker.py

Then in RViz:
    - Fixed Frame: lander
    - Add -> Marker, topic: /lander/marker

Parameters (override with e.g. --ros-args -p scale:=0.2):
    frame_id : TF frame to attach the mesh to (default: lander)
    mesh     : absolute path to the STL (default: source-tree path)
    scale    : uniform mesh scale, must match the SDF (default: 0.2)
    color    : [r, g, b, a] tint for the untextured STL (default: gold)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSHistoryPolicy
from visualization_msgs.msg import Marker

# Decimated (~20k tri) copy of the lander STL. The full-res mesh (1.4M tri)
# crashes RViz's marker loader; Gazebo still uses the full-res one.
DEFAULT_MESH = (
    "/home/xr-dev/ros2_ws/src/leo_simulator-ros2/leo_gz_worlds/"
    "models/argonaut_lander/meshes/Argonaut_TASI_Newlander_01_viz.stl"
)


class LanderMarker(Node):
    def __init__(self):
        super().__init__("lander_rviz_marker")

        self.frame_id = self.declare_parameter("frame_id", "lander").value
        self.mesh = self.declare_parameter("mesh", DEFAULT_MESH).value
        self.scale = float(self.declare_parameter("scale", 0.2).value)
        self.color = self.declare_parameter("color", [0.85, 0.65, 0.13, 1.0]).value

        # Latched-style QoS so a late RViz subscriber still receives the marker.
        qos = QoSProfile(
            depth=1,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            history=QoSHistoryPolicy.KEEP_LAST,
        )
        self.pub = self.create_publisher(Marker, "lander/marker", qos)

        # Republish once a second as a robustness fallback.
        self.timer = self.create_timer(1.0, self.publish_marker)
        self.publish_marker()
        self.get_logger().info(
            f"Publishing lander mesh '{self.mesh}' in frame '{self.frame_id}' "
            f"on /lander/marker"
        )

    def publish_marker(self):
        m = Marker()
        m.header.frame_id = self.frame_id
        m.header.stamp = self.get_clock().now().to_msg()
        m.ns = "lander_model"
        m.id = 0
        m.type = Marker.MESH_RESOURCE
        m.action = Marker.ADD
        m.mesh_resource = "file://" + self.mesh
        # STL has no embedded material -> tint with the marker color.
        m.mesh_use_embedded_materials = False
        m.pose.orientation.w = 1.0  # identity; lander frame == model origin
        m.scale.x = m.scale.y = m.scale.z = self.scale
        m.color.r, m.color.g, m.color.b, m.color.a = [float(c) for c in self.color]
        self.pub.publish(m)


def main():
    rclpy.init()
    node = LanderMarker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
