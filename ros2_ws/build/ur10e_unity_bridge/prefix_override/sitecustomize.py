import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/eric/EricBerg/Chalmers/Kandidatarbete/ros2_ws/install/ur10e_unity_bridge'
