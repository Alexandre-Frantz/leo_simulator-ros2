# Copyright 2023 Fictionlab sp. z o.o.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.actions import IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, TextSubstitution
from launch_ros.actions import Node


def _spawn_robots(context, pkg_project_gazebo):
    """Create a spawn IncludeLaunchDescription for each namespace in robot_ns. """
    ns_raw = LaunchConfiguration("robot_ns").perform(context) or ""
    
    # Allow both comma-separated and space-separated lists
    parts = [p.strip() for p in ns_raw.replace(",", " ").split() if p.strip()]
    
    if not parts:
        parts = ["leo04"]
    
    # Create list of robot spawners based on provided namespaces 
    spawners = []
    for ns in parts:
        spawners.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_project_gazebo, "launch", "spawn_multi_robot.launch.py")
                ),
                launch_arguments={
                    "robot_ns": TextSubstitution(text=ns)
                }.items(),
            )
        )
    return spawners

def generate_launch_description():
    # Setup project paths
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    pkg_project_gazebo = get_package_share_directory("leo_gz_bringup")
    pkg_project_worlds = get_package_share_directory("leo_gz_worlds")
    lidar_bridge_config = os.path.join(
      get_package_share_directory('leo_gz_bringup'),
      'config',
      'gz_bridge.yaml'
      )

    sim_world = DeclareLaunchArgument(
        "sim_world",
        default_value=os.path.join(pkg_project_worlds, "worlds", "leo_empty.sdf"),
        description="Path to the Gazebo world file",
    )

    robot_ns = DeclareLaunchArgument(
        "robot_ns",
        default_value="leo04",
        description="Space or comma-separated list of robot namespaces",
    )

    lander = DeclareLaunchArgument(
        "lander",
        default_value="false",
        description="If true, publish the static TF lander -> lander_lidar_link "
                    "(use with a world that contains the argonaut_lander model)",
    )

    # Static TF anchoring the lander's reference LiDAR to the lander frame.
    # z=1.85 matches the sensor <pose> offset in argonaut_lander/model.sdf.
    # Only spawned when lander:=true.
    lander_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="lander_lidar_static_tf",
        arguments=[
            "--x", "0", "--y", "0", "--z", "1.85",
            "--roll", "0", "--pitch", "0", "--yaw", "0",
            "--frame-id", "lander",
            "--child-frame-id", "lander_lidar_link",
        ],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(LaunchConfiguration("lander")),
        output="screen",
    )

    # RViz mesh marker of the lander (STL has no URDF), in the `lander` frame.
    # Only spawned when lander:=true.
    lander_marker = Node(
        package="leo_gz_bringup",
        executable="lander_rviz_marker",
        name="lander_rviz_marker",
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(LaunchConfiguration("lander")),
        output="screen",
    )

    # Setup to launch the simulator and Gazebo world
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": LaunchConfiguration("sim_world")}.items(),
    )

    # Bridge ROS topics and Gazebo messages for establishing communication
    topic_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="clock_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
        ],
        parameters=[
            {
                "qos_overrides./tf_static.publisher.durability": "transient_local",
            }
        ],
        output="screen",
    )
    
    lidar_topic_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="lidar_bridge",
        parameters=[
            {
                # "qos_overrides./tf_static.publisher.durability": "transient_local",
                "config_file": lidar_bridge_config,
            }
        ],
        output="screen",
    )

    # Build robot spawners dynamically from the list args
    spawn_multi_robots = OpaqueFunction(
        function=_spawn_robots, kwargs={"pkg_project_gazebo" : pkg_project_gazebo}
    )

    return LaunchDescription(
        [
            sim_world,
            robot_ns,
            lander,
            gz_sim,
            spawn_multi_robots,
            topic_bridge,
            lidar_topic_bridge,
            lander_tf,
            lander_marker,
        ]
    )
