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
        
        self.pending_processes = {}
        
        self.main_timer = self.create_timer(0.01, self.main_loop)
        
        self.next_generation_time = time.time() + random.uniform(5.0, 6.0)
        
        self.process_publisher = self.create_publisher(String, 'process_requests', 10)
        self.duration_priority_publisher = self.create_publisher(String, 'process_durations', 10)

        self.process_publisher_RR = self.create_publisher(String, 'process_requests_RR', 10)
        self.duration_priority_publisher_RR = self.create_publisher(String, 'process_durations_RR', 10)

        self.process_publisher_Pri = self.create_publisher(String, 'process_requests_Priority', 10)
        self.duration_priority_publisher_Pri = self.create_publisher(String, 'process_durations_Priority', 10)
        
        self.create_timer(0.05, self.publish_pending_processes)
        
        self.get_logger().info("Process Generator Node started with robust process generation.")
    
    def main_loop(self):
        current_time = time.time()
        
        if current_time >= self.next_generation_time and self.number_of_processes < self.max_processes:
            self.generate_process()
            self.number_of_processes += 1 
            self.next_generation_time = current_time + random.uniform(1.0, 3.5)
            
            if self.number_of_processes >= self.max_processes:
                self.get_logger().info(f"Reached maximum number of processes ({self.max_processes}). Stopping generation.")
    
    def generate_process(self):
        """Generate new process and store info for reliable publishing"""
        process_name = f"P{self.process_counter}"
        self.process_counter += 1
        duration = round(random.triangular(4, 20, 6), 2) 
        priority = random.randint(1, 10)
        
        self.pending_processes[process_name] = {
            'duration': duration,
            'priority': priority,
            'attempts': 0,
            'published_duration': False,
            'published_request': False
        }
        
        self.get_logger().info(f"Generated process: {process_name} (Duration: {duration:.2f}s, Priority: {priority})")
    
    def publish_pending_processes(self):

        processes_to_remove = []
        
        for process_name, info in self.pending_processes.items():
            try:
                duration_msg = String()
                duration_msg.data = f"{process_name}:{info['duration']:.2f}:{info['priority']}"
                
                request_msg = String()
                request_msg.data = process_name
                
                if not info['published_duration']:
                    self.duration_priority_publisher.publish(duration_msg)
                    self.duration_priority_publisher_RR.publish(duration_msg)
                    self.duration_priority_publisher_Pri.publish(duration_msg)
                    info['published_duration'] = True
                    self.get_logger().debug(f"Published duration info for {process_name}")
                
                if info['published_duration'] and not info['published_request']:
                    if info['attempts'] == 0:
                        info['attempts'] += 1
                        continue 
                    
                    self.process_publisher.publish(request_msg)
                    self.process_publisher_RR.publish(request_msg)
                    self.process_publisher_Pri.publish(request_msg)
                    info['published_request'] = True
                    self.get_logger().debug(f"Published process request for {process_name}")
                
                if info['published_duration'] and info['published_request']:
                    processes_to_remove.append(process_name)
                    self.get_logger().info(f"Successfully published all info for {process_name}")
                
            except Exception as e:
                self.get_logger().error(f"Error publishing process {process_name}: {str(e)}")
                info['attempts'] += 1
                if info['attempts'] > 10: 
                    processes_to_remove.append(process_name)
        
        for process_name in processes_to_remove:
            del self.pending_processes[process_name]

def main():
    rclpy.init()
    node = ProcessGeneratorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Process Generator shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()