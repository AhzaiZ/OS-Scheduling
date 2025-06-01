import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/az/Desktop/ros2_ws/install/cpu_scheduler'
