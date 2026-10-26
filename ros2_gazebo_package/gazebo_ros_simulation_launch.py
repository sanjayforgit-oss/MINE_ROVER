"""
ROS 2 Launch File for M.I.N.E.R.S. Rover Gazebo Physics Simulation & RViz SLAM
-----------------------------------------------------------------------------
Launches Gazebo Sim World, Robot URDF Model Publisher, Autonomous SLAM Engine,
Nav2 Costmap Planner, and RViz Visualization Dashboard.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    world_file = os.path.join(pkg_dir, "mine_drift_gazebo.world")
    urdf_file = os.path.join(pkg_dir, "miners_rover.urdf.xacro")
    
    return LaunchDescription([
        # Declare Arguments
        DeclareLaunchArgument(
            'world',
            default_value=world_file,
            description='Full path to Gazebo world file'
        ),
        
        # 1. Launch Gazebo Simulator World
        ExecuteProcess(
            cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_factory.so', LaunchConfiguration('world')],
            output='screen'
        ),

        # 2. Robot State Publisher Node
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{'robot_description': urdf_file}]
        ),

        # 3. Spawn M.I.N.E.R.S. Rover into Gazebo Sim
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=['-entity', 'miners_rover', '-file', urdf_file, '-x', '2.0', '-y', '2.0', '-z', '0.15'],
            output='screen'
        ),

        # 4. Launch Autonomous Navigation & SLAM Engine Node
        Node(
            package='miners_navigation',
            executable='autonomous_nav_engine.py',
            name='autonomous_nav_engine',
            output='screen'
        ),

        # 5. Launch RViz2 Visualization Dashboard
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])
