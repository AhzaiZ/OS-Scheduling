def process_completed(self, msg):
        """Handle process completion notifications"""
        # Keep this for compatibility with the monitoring system
        process_name = msg.data
        self.get_logger().debug(f"Received completion notification for {process_name}")
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from collections import deque
import time

class FCFS(Node):
    def __init__(self):
        super().__init__('FCFS')
        self.queue = deque()
        self.current_process = None
        self.is_cpu_busy = False
        self.process_start_time = None
        self.process_durations = {}
        
        # Main timer that handles scheduling
        self.main_timer = self.create_timer(0.01, self.main_loop)
        
        # Subscribers for process requests and duration info
        self.process_subscriber = self.create_subscription(
            String, 'process_requests', self.handle_process_request, 10)
        
        self.duration_subscriber = self.create_subscription(
            String, 'process_durations', self.handle_process_duration, 10)
        
        self.completion_subscriber = self.create_subscription(
            String, 'process_completed', self.process_completed, 10)
        
        # Publishers
        self.completion_publisher = self.create_publisher(String, 'process_completed', 10)
        self.publisher = self.create_publisher(String, 'scheduled_process', 10)
        
        self.get_logger().info("FCFS Scheduler Node started.")
    
    def main_loop(self):
        current_time = time.time()
        
        # Handle process completion for FCFS's own processes
        if self.is_cpu_busy and self.current_process and self.process_start_time:
            process_duration = self.process_durations.get(self.current_process, 0)
            
            if current_time - self.process_start_time >= process_duration:
                self.complete_current_process()
        
        # Handle scheduling next process for FCFS (only if CPU is free)
        if not self.is_cpu_busy:
            self.schedule_next()
    
    def handle_process_request(self, msg):
        """Handle incoming process requests"""
        process_name = msg.data
        self.queue.append(process_name)
        self.get_logger().info(f"Received process request: {process_name}")
        self.get_logger().info(f"Added process {process_name} to FCFS queue. Queue: {list(self.queue)}")
    
    def handle_process_duration(self, msg):
        """Handle incoming process duration information"""
        try:
            # Parse message format: "process_name:duration:priority"
            parts = msg.data.split(':')
            if len(parts) >= 2:
                process_name = parts[0]
                duration = float(parts[1])
                self.process_durations[process_name] = duration
                self.get_logger().debug(f"Stored duration for {process_name}: {duration:.2f}s")
        except Exception as e:
            self.get_logger().error(f"Error parsing duration message '{msg.data}': {str(e)}")
    
    def complete_current_process(self):
        """Complete the currently running process"""
        if self.current_process:
            duration = self.process_durations.get(self.current_process, 0)
            self.get_logger().info(f"Process {self.current_process} completed execution after {duration:.2f}s")
            
            # Publish completion message with duration info
            msg = String()
            msg.data = f"{self.current_process}:{duration}"  # Include original duration
            self.completion_publisher.publish(msg)
            
            # Reset CPU state
            self.current_process = None
            self.is_cpu_busy = False
            self.process_start_time = None
    

    
    def schedule_next(self):
        """Schedule the next process from the queue"""
        if not self.is_cpu_busy and self.queue:
            next_process = self.queue.popleft()
            
            # Check if we have duration info for this process
            if next_process not in self.process_durations:
                self.get_logger().warning(f"No duration info for process {next_process}, skipping")
                return
            
            # Set up process execution
            self.current_process = next_process
            self.is_cpu_busy = True
            self.process_start_time = time.time()
            
            # Publish that this process is now scheduled/running
            msg = String()
            msg.data = next_process
            self.publisher.publish(msg)
            
            duration = self.process_durations[next_process]
            self.get_logger().info(f"FCFS: Started executing process {next_process} (Duration: {duration:.2f}s)")
            self.get_logger().info(f"Remaining FCFS queue: {list(self.queue)}")
    
    def process_completed(self, msg):
        """Handle process completion notifications"""
        # Keep this for compatibility with the monitoring system
        process_name = msg.data
        self.get_logger().debug(f"Received completion notification for {process_name}")

def main():
    rclpy.init()
    node = FCFS()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 FCFS Scheduler shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()