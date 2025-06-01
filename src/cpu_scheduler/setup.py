from setuptools import find_packages, setup

package_name = 'cpu_scheduler'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(where='.', include=['cpu_scheduler']),
    package_dir={'': '.'},
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/scheduler.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='az',
    maintainer_email='hamadasamer2@hotmail.com',
    description='FCFS CPU scheduling simulation with ROS2 Jazzy and RViz',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'process_node = cpu_scheduler.process_node:main',
            'visualization_node = cpu_scheduler.visualization_node:main',
            'terminal_monitor = cpu_scheduler.terminal_monitor:main',
            'FCFS = cpu_scheduler.FCFS:main',
            'round_robin = cpu_scheduler.round_robin:main',
            'Priority_Scheduling = cpu_scheduler.priority:main',
            'process_table_printer = cpu_scheduler.process_table_printer:main'
        ],
    },
)
