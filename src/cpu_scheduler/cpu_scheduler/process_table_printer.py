import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class ProcessTablePrinter(Node):
    def __init__(self):
        super().__init__('process_table_printer')

        self.total_expected_processes = 20
        self.process_ids = []
        self.bursts = {}
        self.priorities = {}

        self.create_subscription(String, 'process_requests', self.handle_request, 10)
        self.create_subscription(String, 'process_durations', self.handle_duration_priority, 10)

        self.get_logger().info("Process Table Printer node started...")

    def handle_request(self, msg: String):
        pid = msg.data.strip()
        if pid not in self.process_ids:
            self.process_ids.append(pid)
            self.get_logger().info(f"Received process request: {pid}")
        self.check_and_print()

    def handle_duration_priority(self, msg: String):
        try:
            pid, burst_str, prio_str = msg.data.strip().split(":")
            burst = float(burst_str)
            prio = int(prio_str)

            self.bursts[pid] = burst
            self.priorities[pid] = prio

            self.get_logger().info(f"Received duration info → {pid}: burst={burst}s, priority={prio}")
            self.check_and_print()
        except ValueError:
            self.get_logger().error(f"Malformed duration message: {msg.data}")

    def check_and_print(self):
        if (
            len(self.process_ids) >= self.total_expected_processes and
            all(pid in self.bursts and pid in self.priorities for pid in self.process_ids)
        ):
            self.print_table()
            rclpy.shutdown()

    def print_table(self):
        print("\n========== Process Summary Table ==========")
        print(f"{'PID':<10}{'CPU Burst (s)':<15}{'Priority':<10}")
        print("-" * 35)
        for pid in self.process_ids:
            burst = self.bursts[pid]
            prio = self.priorities[pid]
            print(f"{pid:<10}{burst:<15.2f}{prio:<10}")
        print("===========================================\n")


def main(args=None):
    rclpy.init(args=args)
    node = ProcessTablePrinter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
