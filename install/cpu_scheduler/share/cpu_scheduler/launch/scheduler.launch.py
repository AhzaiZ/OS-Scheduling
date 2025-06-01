from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Scheduler node
        Node(
            package='cpu_scheduler', 
            executable='FCFS',
            name='FCFS'
        ),

        Node(
            package='cpu_scheduler', 
            executable='round_robin',
            name='RR'
        ),

        Node(
            package='cpu_scheduler', 
            executable='Priority_Scheduling',
            name='Priority_Scheduler'
        ),

        Node(
            package='cpu_scheduler', 
            executable='process_node',
            name='Process_Generator'
        ),
        
        # Terminal monitor for clear scheduling visualization
        # Node(
        #     package='cpu_scheduler', 
        #     executable='terminal_monitor',
        #     name='monitor'
        # ),
        
        Node(
            package='cpu_scheduler', 
            executable='visualization_node',
            name='Visualizer'
        )
    ])