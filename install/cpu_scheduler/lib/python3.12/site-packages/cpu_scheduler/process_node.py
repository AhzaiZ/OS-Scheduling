import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import random
import time

class ProcessGeneratorNode(Node):
    def __init__(self):
        super().__init__('process_generator')
        self.process_counter = 1
        self.next_generation_time = None
        self.number_of_processes = 0
        self.max_processes = 20
        
        # Store process info for reliable publishing
        self.pending_processes = {}  # process_name -> {duration, priority}
        
        # Main timer that handles process generation
        self.main_timer = self.create_timer(0.01, self.main_loop)
        
        # Set initial generation time
        self.next_generation_time = time.time() + random.uniform(5.0, 6.0)
        
        # Publishers for all schedulers
        self.process_publisher = self.create_publisher(String, 'process_requests', 10)
        self.duration_priority_publisher = self.create_publisher(String, 'process_durations', 10)

        self.process_publisher_RR = self.create_publisher(String, 'process_requests_RR', 10)
        self.duration_priority_publisher_RR = self.create_publisher(String, 'process_durations_RR', 10)

        self.process_publisher_Pri = self.create_publisher(String, 'process_requests_Priority', 10)
        self.duration_priority_publisher_Pri = self.create_publisher(String, 'process_durations_Priority', 10)
        
        # Timer for reliable message publishing (separate from main loop)
        self.create_timer(0.05, self.publish_pending_processes)
        
        self.get_logger().info("Process Generator Node started with robust process generation.")
    
    def main_loop(self):
        current_time = time.time()
        
        # Handle process generation
        if current_time >= self.next_generation_time and self.number_of_processes < self.max_processes:
            self.generate_process()
            self.number_of_processes += 1 
            # Schedule next generation
            self.next_generation_time = current_time + random.uniform(1.0, 3.5)
            
            if self.number_of_processes >= self.max_processes:
                self.get_logger().info(f"Reached maximum number of processes ({self.max_processes}). Stopping generation.")
    
    def generate_process(self):
        """Generate new process and store info for reliable publishing"""
        process_name = f"P{self.process_counter}"
        self.process_counter += 1
        duration = round(random.triangular(4, 20, 6), 2)  # float with 2 decimal places
        priority = random.randint(1, 10)
        
        # Store process info
        self.pending_processes[process_name] = {
            'duration': duration,
            'priority': priority,
            'attempts': 0,
            'published_duration': False,
            'published_request': False
        }
        
        self.get_logger().info(f"Generated process: {process_name} (Duration: {duration:.2f}s, Priority: {priority})")
    
    def publish_pending_processes(self):
        """Reliably publish process information with retries"""
        processes_to_remove = []
        
        for process_name, info in self.pending_processes.items():
            try:
                # Prepare messages
                duration_msg = String()
                duration_msg.data = f"{process_name}:{info['duration']:.2f}:{info['priority']}"
                
                request_msg = String()
                request_msg.data = process_name
                
                # Always publish duration info first for all schedulers
                if not info['published_duration']:
                    self.duration_priority_publisher.publish(duration_msg)
                    self.duration_priority_publisher_RR.publish(duration_msg)
                    self.duration_priority_publisher_Pri.publish(duration_msg)
                    info['published_duration'] = True
                    self.get_logger().debug(f"Published duration info for {process_name}")
                
                # Then publish process requests (with small delay to ensure duration is processed)
                if info['published_duration'] and not info['published_request']:
                    # Add small delay only on first attempt
                    if info['attempts'] == 0:
                        info['attempts'] += 1
                        continue  # Skip this cycle to allow duration to be processed
                    
                    self.process_publisher.publish(request_msg)
                    self.process_publisher_RR.publish(request_msg)
                    self.process_publisher_Pri.publish(request_msg)
                    info['published_request'] = True
                    self.get_logger().debug(f"Published process request for {process_name}")
                
                # Mark for removal if both published
                if info['published_duration'] and info['published_request']:
                    processes_to_remove.append(process_name)
                    self.get_logger().info(f"Successfully published all info for {process_name}")
                
            except Exception as e:
                self.get_logger().error(f"Error publishing process {process_name}: {str(e)}")
                info['attempts'] += 1
                if info['attempts'] > 10:  # Give up after 10 attempts
                    processes_to_remove.append(process_name)
        
        # Clean up completed processes
        for process_name in processes_to_remove:
            del self.pending_processes[process_name]

def main():
    rclpy.init()
    node = ProcessGeneratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 Process Generator shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()