import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
from datetime import datetime

class TerminalMonitorNode(Node):
    def __init__(self):
        super().__init__('terminal_monitor')
        
        # Subscribers
        self.request_subscriber = self.create_subscription(
            String, 'process_requests', self.on_process_request, 10)
        self.scheduled_subscriber = self.create_subscription(
            String, 'scheduled_process', self.on_process_scheduled, 10)
        self.completed_subscriber = self.create_subscription(
            String, 'process_completed', self.on_process_completed, 10)
        
        # State tracking
        self.processes = {}
        self.start_time = time.time()
        self.current_running = None
        self.queue = []
        
        print("\n" + "="*60)
        print("        CPU SCHEDULING SIMULATION MONITOR")
        print("="*60)
        print("Time | Event | Process | Status | Queue")
        print("-"*60)
        
        self.get_logger().info("Terminal Monitor started")

    def get_timestamp(self):
        return f"{time.time() - self.start_time:6.1f}s"

    def on_process_request(self, msg):
        process_id = msg.data
        timestamp = self.get_timestamp()
        
        if process_id not in self.processes:
            self.processes[process_id] = {
                'state': 'REQUESTED',
                'request_time': time.time(),
                'start_time': None,
                'end_time': None
            }
            self.queue.append(process_id)
        
        queue_str = " -> ".join(self.queue) if self.queue else "Empty"
        print(f"{timestamp} | REQ   | {process_id:7} | Requested  | {queue_str}")

    def on_process_scheduled(self, msg):
        process_id = msg.data
        timestamp = self.get_timestamp()
        
        if process_id in self.processes:
            self.processes[process_id]['state'] = 'RUNNING'
            self.processes[process_id]['start_time'] = time.time()
            self.current_running = process_id
            
            # Remove from queue
            if process_id in self.queue:
                self.queue.remove(process_id)
        
        queue_str = " -> ".join(self.queue) if self.queue else "Empty"
        print(f"{timestamp} | START | {process_id:7} | Running    | {queue_str}")
        print(f"{'':>6} |       |         | CPU: {process_id} |")

    def on_process_completed(self, msg):
        process_id = msg.data
        timestamp = self.get_timestamp()
        
        if process_id in self.processes:
            self.processes[process_id]['state'] = 'COMPLETED'
            self.processes[process_id]['end_time'] = time.time()
            
            if self.current_running == process_id:
                self.current_running = None
            
            # Calculate metrics
            proc_info = self.processes[process_id]
            if proc_info['start_time'] and proc_info['request_time']:
                waiting_time = proc_info['start_time'] - proc_info['request_time']
                execution_time = proc_info['end_time'] - proc_info['start_time']
                turnaround_time = proc_info['end_time'] - proc_info['request_time']
                
                queue_str = " -> ".join(self.queue) if self.queue else "Empty"
                print(f"{timestamp} | END   | {process_id:7} | Completed  | {queue_str}")
                print(f"{'':>6} |       |         | Wait: {waiting_time:.1f}s, Exec: {execution_time:.1f}s, TAT: {turnaround_time:.1f}s |")
                print(f"{'':>6} |       |         | CPU: IDLE  |")
                
                # Check if all processes are done
                if all(proc['state'] == 'COMPLETED' for proc in self.processes.values()):
                    print("-"*60)
                    print("ALL PROCESSES COMPLETED!")
                    self.print_summary()

    def print_summary(self):
        print("\nSUMMARY:")
        print("-"*40)
        total_waiting = 0
        total_turnaround = 0
        completed_count = 0
        
        for proc_id, info in self.processes.items():
            if info['state'] == 'COMPLETED' and info['start_time'] and info['request_time']:
                waiting_time = info['start_time'] - info['request_time']
                turnaround_time = info['end_time'] - info['request_time']
                execution_time = info['end_time'] - info['start_time']
                
                print(f"{proc_id}: Wait={waiting_time:.1f}s, TAT={turnaround_time:.1f}s, Exec={execution_time:.1f}s")
                
                total_waiting += waiting_time
                total_turnaround += turnaround_time
                completed_count += 1
        
        if completed_count > 0:
            avg_waiting = total_waiting / completed_count
            avg_turnaround = total_turnaround / completed_count
            print(f"\nAverage Waiting Time: {avg_waiting:.1f}s")
            print(f"Average Turnaround Time: {avg_turnaround:.1f}s")
        
        print("="*60)

def main():
    rclpy.init()
    node = TerminalMonitorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    finally:
        node.destroy_node()
        rclpy.shutdown()