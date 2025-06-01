import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import time
import heapq

class PrioritySchedulerNode(Node):
    def __init__(self):
        super().__init__('priority_scheduler')

        self.process_heap = []  # Min-heap of (priority, arrival_time, pid)
        self.priority_map = {}  # pid -> current priority
        self.duration_map = {}  # pid -> duration
        self.arrival_time_map = {}  # pid -> timestamp
        self.pending_processes = set()  # processes waiting for complete info

        self.current_process = None
        self.cpu_busy = False
        self.process_start_time = None
        self.process_duration = 0.0

        # ROS Subscriptions
        self.create_subscription(String, 'process_requests_Priority', self.handle_new_process, 10)
        self.create_subscription(String, 'process_durations_Priority', self.handle_duration_priority, 10)

        # ROS Publishers
        self.scheduler_publisher = self.create_publisher(String, 'scheduled_process_Priority', 10)
        self.completion_publisher = self.create_publisher(String, 'process_completed_Priority', 10)
        self.priority_update_publisher = self.create_publisher(String, 'priority_updates', 10)

        # Main scheduling loop
        self.create_timer(0.01, self.main_loop)
        self.create_timer(20.0, self.apply_aging_timer)

        self.get_logger().info("🚦 Robust Priority Scheduler started (preemptive + aging + simulation).")

    def handle_new_process(self, msg: String):
        pid = msg.data.strip()
        if not pid:
            return
            
        arrival_time = time.time()
        self.arrival_time_map[pid] = arrival_time
        
        # Check if we have complete info
        if pid in self.duration_map and pid in self.priority_map:
            heapq.heappush(self.process_heap, (self.priority_map[pid], arrival_time, pid))
            self.get_logger().info(f"📥 Received {pid} with priority {self.priority_map[pid]}")
            if pid in self.pending_processes:
                self.pending_processes.remove(pid)
        else:
            # Store as pending
            self.pending_processes.add(pid)
            self.get_logger().debug(f"Process {pid} pending - waiting for duration/priority info")

    def handle_duration_priority(self, msg: String):
        try:
            parts = msg.data.split(":")
            if len(parts) >= 3:
                pid, duration_str, priority_str = parts[0].strip(), parts[1], parts[2]
                self.duration_map[pid] = float(duration_str)
                self.priority_map[pid] = float(priority_str)
                self.get_logger().info(f"📊 {pid} → duration: {duration_str}s, priority: {priority_str}")
                
                # Check if this process was pending
                if pid in self.pending_processes and pid in self.arrival_time_map:
                    heapq.heappush(self.process_heap, (self.priority_map[pid], self.arrival_time_map[pid], pid))
                    self.pending_processes.remove(pid)
                    self.get_logger().info(f"📥 Activated pending process {pid}")
                    
        except (ValueError, IndexError) as e:
            self.get_logger().error(f"❌ Bad format in process_durations: {msg.data} - {str(e)}")

    def check_process_completion(self):
        """Check if current process has completed based on simulated duration"""
        if not self.cpu_busy or not self.current_process or not self.process_start_time:
            return False
        
        elapsed_time = time.time() - self.process_start_time
        if elapsed_time >= self.process_duration:
            self.get_logger().info(f"✅ {self.current_process} completed after {elapsed_time:.2f}s.")
            
            # Publish completion message
            completion_msg = String()
            completion_msg.data = self.current_process
            self.completion_publisher.publish(completion_msg)
            
            # Reset CPU state
            self.cpu_busy = False
            self.current_process = None
            self.process_start_time = None
            self.process_duration = 0.0
            return True
        
        return False

    def apply_aging_timer(self):
        """Timer callback for aging - separate from main loop"""
        self.apply_aging()

    def apply_aging(self):
        now = time.time()
        aged_heap = []
        priority_updates = []  # Track which priorities changed

        for (priority, arrival_time, pid) in self.process_heap:
            old_priority = priority
            if now - arrival_time > 40.0 and priority > 1:
                new_priority = priority - 1
            else:
                new_priority = priority
            aged_heap.append((new_priority, arrival_time, pid))
            
            # Update internal map and track changes
            self.priority_map[pid] = new_priority
            
            # If priority changed, record it for publishing
            if old_priority != new_priority:
                priority_updates.append((pid, new_priority))

        heapq.heapify(aged_heap)
        self.process_heap = aged_heap
    
        # Publish priority updates for processes that changed
        for pid, new_priority in priority_updates:
            update_msg = String()
            update_msg.data = f"{pid}:{new_priority}"
            self.priority_update_publisher.publish(update_msg)
            self.get_logger().info(f"📈 Priority updated: {pid} -> {new_priority}")



    def preempt_if_needed(self):
        if not self.cpu_busy or not self.current_process:
            return False

        if not self.process_heap:
            return False

        top_priority, _, top_pid = self.process_heap[0]
        current_priority = self.priority_map[self.current_process]

        if top_priority < current_priority and top_pid != self.current_process:
            self.get_logger().info(f"⚠️ Preempting {self.current_process} for higher priority {top_pid}")
            
            # Calculate remaining time for preempted process
            elapsed_time = time.time() - self.process_start_time
            remaining_duration = self.process_duration - elapsed_time
            
            # Update duration map with remaining time
            self.duration_map[self.current_process] = max(0.0, remaining_duration)
            
            # Put preempted process back in heap
            heapq.heappush(self.process_heap, (current_priority, self.arrival_time_map[self.current_process], self.current_process))
            
            # Publish current priority for the preempted process (in case it was aged)
            priority_update_msg = String()
            priority_update_msg.data = f"{self.current_process}:{current_priority}"
            self.priority_update_publisher.publish(priority_update_msg)
            
            # Reset CPU state
            self.current_process = None
            self.cpu_busy = False
            self.process_start_time = None
            self.process_duration = 0.0
            return True

        return False

    def main_loop(self):
        # Check if current process has completed
        if self.check_process_completion():
            # Process completed, CPU is now free
            pass

        # Check for preemption
        self.preempt_if_needed()
        
        # Schedule next process if CPU is free
        if not self.cpu_busy and self.process_heap:
            priority, _, pid = heapq.heappop(self.process_heap)
            self.current_process = pid
            self.cpu_busy = True
            self.process_start_time = time.time()
            self.process_duration = self.duration_map[pid]  # Set simulated duration

            # Publish scheduled process
            msg = String()
            msg.data = pid
            self.scheduler_publisher.publish(msg)
            self.get_logger().info(f"🚀 Running: {pid} (priority {priority:.2f}, duration {self.process_duration:.2f}s)")

def main():
    rclpy.init()
    node = PrioritySchedulerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("🛑 Priority Scheduler shutting down.")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()