import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32
from collections import deque
import time

class RoundRobinScheduler(Node):
    def __init__(self):
        super().__init__('round_robin_scheduler')
        self.queue = deque()
        self.process_durations = {}
        self.remaining_time = {}
        self.pending_processes = set()  # processes waiting for duration info
        self.current_process = None
        self.process_start_time = None
        self.base_quantum = 6.0  # base quantum in seconds
        self.current_quantum = 6.0  # current active quantum
        self.is_cpu_busy = False
        
        # Track preemption count for each process
        self.preemption_count = {}
        
        # Subscriptions
        self.create_subscription(String, 'process_requests_RR', self.add_process, 10)
        self.create_subscription(String, 'process_durations_RR', self.update_duration, 10)
        self.create_subscription(Float32, 'quantum_update', self.update_quantum, 10)
        
        # Publishers
        self.publisher = self.create_publisher(String, 'scheduled_process_RR', 10)
        self.completion_publisher = self.create_publisher(String, 'process_completed_RR', 10)
        self.quantum_publisher = self.create_publisher(Float32, 'quantum_update', 10)
        
        # Timer for scheduling - check every 10ms
        self.create_timer(0.01, self.schedule)
        
        self.get_logger().info('🌀 Enhanced Round Robin Scheduler with Progressive Quantum initialized.')
    
    def add_process(self, msg):
        pid = msg.data.strip()
        if not pid:
            return
            
        # Initialize preemption count for new process
        if pid not in self.preemption_count:
            self.preemption_count[pid] = 0
            
        # Check if we have duration info
        if pid in self.process_durations:
            if pid not in self.queue and pid not in self.pending_processes:
                self.queue.append(pid)
                self.get_logger().info(f'➕ Process added to queue: {pid}. Queue: {list(self.queue)}')
        else:
            # Store as pending
            if pid not in self.pending_processes:
                self.pending_processes.add(pid)
                self.get_logger().debug(f'Process {pid} pending - waiting for duration info')
    
    def update_duration(self, msg):
        try:
            parts = msg.data.split(":")
            if len(parts) >= 2:
                pid = parts[0].strip()
                duration = float(parts[1])
                self.process_durations[pid] = duration
                self.remaining_time[pid] = duration
                
                # Initialize preemption count if not exists
                if pid not in self.preemption_count:
                    self.preemption_count[pid] = 0
                    
                self.get_logger().info(f'⏱ Duration for {pid} set to {duration:.2f}s')
                
                # Check if this process was pending
                if pid in self.pending_processes:
                    self.queue.append(pid)
                    self.pending_processes.remove(pid)
                    self.get_logger().info(f'➕ Activated pending process: {pid}. Queue: {list(self.queue)}')
                    
        except Exception as e:
            self.get_logger().error(f'Failed to parse duration message: {msg.data} - {str(e)}')
    
    def update_quantum(self, msg):
        self.current_quantum = float(msg.data)
        self.get_logger().info(f'🔄 Time quantum updated to {self.current_quantum:.2f} seconds')
    
    def calculate_quantum_for_process(self, process_name):
        """Calculate quantum based on preemption count"""
        preemptions = self.preemption_count.get(process_name, 0)
        
        # Progressive quantum: 5, 10, 20, 40, etc. (doubles each time after first preemption)
        if preemptions == 0:
            return self.base_quantum
        elif preemptions == 1:
            return self.base_quantum * 2  # 10
        else:
            # For 2+ preemptions: 20, 40, 80, etc.
            return self.base_quantum * (2 ** preemptions)
    
    def set_quantum_for_current_process(self):
        """Set the quantum for the current process and publish the update"""
        if self.current_process:
            new_quantum = self.calculate_quantum_for_process(self.current_process)
            
            # Only update if quantum changed
            if abs(new_quantum - self.current_quantum) > 0.01:
                self.current_quantum = new_quantum
                
                # Publish quantum update
                quantum_msg = Float32()
                quantum_msg.data = new_quantum
                self.quantum_publisher.publish(quantum_msg)
                
                preemptions = self.preemption_count.get(self.current_process, 0)
                self.get_logger().info(f'🔄 Quantum set to {new_quantum:.2f}s for {self.current_process} (preemptions: {preemptions})')
    
    def schedule(self):
        current_time = time.time()
        
        # If CPU is busy, check if current process should be preempted or completed
        if self.is_cpu_busy and self.current_process:
            self.handle_running_process(current_time)
        
        # If CPU is free and we have processes waiting, start the next one
        elif not self.is_cpu_busy and self.queue:
            self.start_next_process(current_time)
    
    def start_next_process(self, current_time):
        """Start the next process from the queue"""
        if self.queue:
            ready_process = self.queue.popleft()
            self.current_process = ready_process
            self.process_start_time = current_time
            self.is_cpu_busy = True
            
            # Set quantum for this process
            self.set_quantum_for_current_process()
            
            remaining_time = self.remaining_time.get(ready_process, 0.0)
            total_duration = self.process_durations.get(ready_process, 0.0)
            preemptions = self.preemption_count.get(ready_process, 0)
            
            self.get_logger().info(f'🟢 Starting process: {ready_process} (Total: {total_duration:.2f}s, Remaining: {remaining_time:.2f}s, Preemptions: {preemptions}, Quantum: {self.current_quantum:.2f}s)')
            
            # Publish the scheduled process
            msg = String()
            msg.data = ready_process
            self.publisher.publish(msg)
    
    def handle_running_process(self, current_time):
        """Handle the currently running process"""
        if not self.process_start_time:
            self.get_logger().warning("Process running but no start time recorded!")
            return
        
        elapsed_time = current_time - self.process_start_time
        remaining = self.remaining_time.get(self.current_process, 0.0)
        
        # Check if quantum expired or process should complete
        quantum_expired = elapsed_time >= self.current_quantum
        process_completed = elapsed_time >= remaining
        
        if quantum_expired or process_completed:
            # Calculate actual time used (minimum of elapsed, quantum, and remaining)
            time_used = min(elapsed_time, self.current_quantum, remaining)
            
            # Update remaining time
            self.remaining_time[self.current_process] -= time_used
            
            # Check if process is completed
            if self.remaining_time[self.current_process] <= 0.01:  # Small epsilon for floating point comparison
                self.complete_process()
            else:
                self.preempt_process()
    
    def complete_process(self):
        """Complete the current process"""
        process_name = self.current_process
        elapsed_time = time.time() - self.process_start_time if self.process_start_time else 0
        preemptions = self.preemption_count.get(process_name, 0)
        
        self.get_logger().info(f'✅ Process {process_name} completed after {elapsed_time:.2f}s (Total preemptions: {preemptions}).')
        
        # Publish completion
        msg = String()
        msg.data = process_name
        self.completion_publisher.publish(msg)
        
        # Clean up
        if process_name in self.remaining_time:
            del self.remaining_time[process_name]
        if process_name in self.process_durations:
            del self.process_durations[process_name]
        if process_name in self.preemption_count:
            del self.preemption_count[process_name]
        
        self.reset_cpu()
    
    def preempt_process(self):
        """Preempt the current process (quantum expired but not finished)"""
        process_name = self.current_process
        remaining = self.remaining_time.get(process_name, 0.0)
        elapsed_time = time.time() - self.process_start_time if self.process_start_time else 0
        
        # Increment preemption count
        self.preemption_count[process_name] = self.preemption_count.get(process_name, 0) + 1
        preemptions = self.preemption_count[process_name]
        next_quantum = self.calculate_quantum_for_process(process_name)
        
        self.get_logger().info(f'⏸ Process {process_name} preempted after {elapsed_time:.2f}s. Remaining: {remaining:.2f}s (Preemptions: {preemptions}, Next quantum: {next_quantum:.2f}s)')
        
        # Add back to queue for next round
        self.queue.append(process_name)
        
        self.reset_cpu()
    
    def reset_cpu(self):
        """Reset CPU state"""
        self.current_process = None
        self.is_cpu_busy = False
        self.process_start_time = None
        # Reset quantum to base quantum when no specific process is running
        self.current_quantum = self.base_quantum
        
        # Publish quantum reset to base value
        quantum_msg = Float32()
        quantum_msg.data = self.base_quantum
        self.quantum_publisher.publish(quantum_msg)

def main():
    rclpy.init()
    node = RoundRobinScheduler()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('🛑 Enhanced Round Robin Scheduler shutting down.')
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()