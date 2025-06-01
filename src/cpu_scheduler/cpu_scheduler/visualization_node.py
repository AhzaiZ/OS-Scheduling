import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point
from builtin_interfaces.msg import Duration
import time
import random

class TripleVisualizationNode(Node):
    def __init__(self):
        super().__init__('triple_visualization_node')
        
        
        self.fcfs_scheduled_subscriber = self.create_subscription(
            String, 'scheduled_process', self.on_fcfs_process_scheduled, 10)
        self.fcfs_completed_subscriber = self.create_subscription(
            String, 'process_completed', self.on_fcfs_process_completed, 10)
        self.fcfs_request_subscriber = self.create_subscription(
            String, 'process_requests', self.on_fcfs_process_request, 10)
        
       
        self.rr_scheduled_subscriber = self.create_subscription(
            String, 'scheduled_process_RR', self.on_rr_process_scheduled, 10)
        self.rr_completed_subscriber = self.create_subscription(
            String, 'process_completed_RR', self.on_rr_process_completed, 10)
        self.rr_request_subscriber = self.create_subscription(
            String, 'process_requests', self.on_rr_process_request, 10)
        
        self.priority_scheduled_subscriber = self.create_subscription(
            String, 'scheduled_process_Priority', self.on_priority_process_scheduled, 10)
        self.priority_completed_subscriber = self.create_subscription(
            String, 'process_completed_Priority', self.on_priority_process_completed, 10)
        self.priority_request_subscriber = self.create_subscription(
            String, 'process_requests', self.on_priority_process_request, 10)
        self.priority_duration_subscriber = self.create_subscription(
            String, 'process_durations', self.on_priority_duration_info, 10)
        self.priority_update_subscriber = self.create_subscription(
            String, 'priority_updates', self.on_priority_update, 10)
        
       
        self.marker_publisher = self.create_publisher(MarkerArray, 'triple_visualization_marker_array', 10)
        

        self.fcfs_process_states = {}
        self.rr_process_states = {}
        self.priority_process_states = {}
        
        self.fcfs_current_running = None
        self.rr_current_running = None
        self.priority_current_running = None
        
        self.fcfs_completed_order = []
        self.rr_completed_order = []
        self.priority_completed_order = []
        
        self.priority_info = {} 
        self.original_priorities = {}
        
        self.display_timer = self.create_timer(0.1, self.update_display)
        
        self.get_logger().info("Triple Scheduler Visualization Node started - comparing FCFS, Round Robin, and Priority")

    def on_priority_duration_info(self, msg):
        """Handle priority and duration information for Priority scheduler"""
        try:
            pid, duration_str, priority_str = msg.data.split(":")
            priority_val = float(priority_str)
            self.priority_info[pid] = {
                'duration': float(duration_str),
                'priority': priority_val
            }
            
            if pid not in self.original_priorities:
                self.original_priorities[pid] = priority_val
                
            self.get_logger().info(f"Priority: Process {pid} info - Duration: {duration_str}s, Priority: {priority_str}")
        except ValueError:
            self.get_logger().error(f"Bad format in process_durations: {msg.data}")


    def on_priority_process_request(self, msg):
        """Handle process requests for Priority scheduling"""
        process_id = msg.data
        if process_id not in self.priority_process_states:
            current_time = time.time()
            
            priority_val = self.priority_info.get(process_id, {}).get('priority', 0.0)
            duration_val = self.priority_info.get(process_id, {}).get('duration', 0.0)
            
            if process_id not in self.original_priorities:
                self.original_priorities[process_id] = priority_val
            
            self.priority_process_states[process_id] = {
                'state': 'WAITING',
                'position': len(self.priority_process_states),
                'start_time': None,
                'total_time': 0.0,
                'wait_start': current_time,
                'cpu_burst': None,
                'wait_time': 0.0,
                'turnaround_time': 0.0,
                'response_time': None, 
                'first_execution_time': None, 
                'arrival_time': current_time,
                'preemption_count': 0,
                'completion_time': None,
                'priority': priority_val,  
                'expected_duration': duration_val
            }
            self.get_logger().info(f"Priority: Process {process_id} added (WAITING) - Priority: {priority_val}")


    def on_priority_process_scheduled(self, msg):
        process_id = msg.data
        if process_id in self.priority_process_states:
            current_time = time.time()
            
            if self.priority_current_running and self.priority_current_running in self.priority_process_states:
                if self.priority_process_states[self.priority_current_running]['state'] == 'RUNNING':
                    prev_process = self.priority_process_states[self.priority_current_running]
                    if prev_process['start_time']:
                        prev_process['total_time'] += current_time - prev_process['start_time']
                    if self.priority_current_running != process_id:
                        self.priority_process_states[self.priority_current_running]['start_time'] = None
                        self.priority_process_states[self.priority_current_running]['state'] = 'WAITING'
                        self.priority_process_states[self.priority_current_running]['wait_start'] = current_time
                        self.priority_process_states[self.priority_current_running]['preemption_count'] += 1
            
            process_info = self.priority_process_states[process_id]
            if process_info['wait_start'] and process_info['state'] == 'WAITING':
                process_info['wait_time'] += current_time - process_info['wait_start']
            
            if process_info['first_execution_time'] is None:
                process_info['first_execution_time'] = current_time
                if process_info['arrival_time']:
                    process_info['response_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'RUNNING'
            process_info['start_time'] = current_time
            self.priority_current_running = process_id
            self.get_logger().info(f"Priority: Process {process_id} is now RUNNING (Priority: {process_info['priority']}, Total wait time: {process_info['wait_time']:.2f}s, Response time: {process_info['response_time']:.2f}s)")


    def on_priority_update(self, msg):
        """Handle priority updates from aging or other priority changes"""
        try:
            parts = msg.data.split(":")
            if len(parts) >= 2:
                pid = parts[0].strip()
                new_priority = float(parts[1])
                
                if pid not in self.original_priorities:
                   
                    current_priority = self.priority_process_states.get(pid, {}).get('priority', new_priority)
                    self.original_priorities[pid] = current_priority
                
                if pid in self.priority_process_states:
                    old_priority = self.priority_process_states[pid].get('priority', 0.0)
                    self.priority_process_states[pid]['priority'] = new_priority
                    self.get_logger().info(f"Priority updated for {pid}: {old_priority:.1f} -> {new_priority:.1f}")
                
                if pid in self.priority_info:
                    self.priority_info[pid]['priority'] = new_priority
                else:
                    self.priority_info[pid] = {
                        'priority': new_priority,
                        'duration': 0.0  # Will be updated when duration info comes
                    }
                    
        except (ValueError, IndexError) as e:
            self.get_logger().error(f" Bad format in priority_updates: {msg.data} - {str(e)}")



    def on_priority_process_completed(self, msg):
        process_id = msg.data
        if process_id in self.priority_process_states:
            current_time = time.time()
            process_info = self.priority_process_states[process_id]
            
            if process_info['start_time']:
                process_info['total_time'] += current_time - process_info['start_time']
            
            process_info['cpu_burst'] = process_info['total_time']
            
            if process_info['arrival_time']:
                process_info['turnaround_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'COMPLETED'
            process_info['completion_time'] = current_time
            
            self.priority_completed_order.insert(0, process_id)
            
            if self.priority_current_running == process_id:
                self.priority_current_running = None
            
            response_time_str = f"{process_info['response_time']:.2f}s" if process_info['response_time'] is not None else "N/A"
            self.get_logger().info(f"Priority: Process {process_id} COMPLETED - CPU: {process_info['total_time']:.2f}s, Wait: {process_info['wait_time']:.2f}s, Response: {response_time_str}, TAT: {process_info['turnaround_time']:.2f}s, Preemptions: {process_info['preemption_count']}")

    def on_rr_process_request(self, msg):
        """Handle process requests specifically for Round Robin tracking"""
        process_id = msg.data
        if process_id not in self.rr_process_states:
            current_time = time.time()
            self.rr_process_states[process_id] = {
                'state': 'WAITING',
                'position': len(self.rr_process_states),
                'start_time': None,
                'total_time': 0.0,
                'wait_start': current_time,
                'cpu_burst': None,
                'wait_time': 0.0,
                'turnaround_time': 0.0,
                'response_time': None,  
                'first_execution_time': None,  
                'arrival_time': current_time,
                'preemption_count': 0,
                'completion_time': None
            }
            self.get_logger().info(f"RR: Process {process_id} added (WAITING)")

    def on_fcfs_process_request(self, msg):
        process_id = msg.data
        if process_id not in self.fcfs_process_states:
            current_time = time.time()
            self.fcfs_process_states[process_id] = {
                'state': 'WAITING',
                'position': len(self.fcfs_process_states),
                'start_time': None,
                'total_time': 0.0,
                'wait_start': current_time,
                'cpu_burst': None,
                'wait_time': 0.0,
                'turnaround_time': 0.0,
                'response_time': None,  
                'first_execution_time': None, 
                'arrival_time': current_time,
                'completion_time': None
            }
            self.get_logger().info(f"FCFS: Process {process_id} added (WAITING)")

    def on_fcfs_process_scheduled(self, msg):
        process_id = msg.data
        if process_id in self.fcfs_process_states:
            current_time = time.time()
            
            if self.fcfs_current_running and self.fcfs_current_running in self.fcfs_process_states:
                if self.fcfs_process_states[self.fcfs_current_running]['state'] == 'RUNNING':
                    prev_process = self.fcfs_process_states[self.fcfs_current_running]
                    if prev_process['start_time']:
                        prev_process['total_time'] += current_time - prev_process['start_time']
            
            process_info = self.fcfs_process_states[process_id]
            if process_info['wait_start']:
                process_info['wait_time'] = current_time - process_info['wait_start']
            
            if process_info['first_execution_time'] is None:
                process_info['first_execution_time'] = current_time
                if process_info['arrival_time']:
                    process_info['response_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'RUNNING'
            process_info['start_time'] = current_time
            self.fcfs_current_running = process_id
            self.get_logger().info(f"FCFS: Process {process_id} is now RUNNING (Wait time: {process_info['wait_time']:.2f}s, Response time: {process_info['response_time']:.2f}s)")

    def on_fcfs_process_completed(self, msg):
        parts = msg.data.split(':')
        process_id = parts[0]
        original_duration = float(parts[1]) if len(parts) > 1 else None
        if process_id in self.fcfs_process_states:
            current_time = time.time()
            process_info = self.fcfs_process_states[process_id]
            
            if process_info['start_time']:
                final_execution_time = current_time - process_info['start_time']
                process_info['total_time'] = final_execution_time  # Set, don't add
            
            process_info['cpu_burst'] = original_duration if original_duration else process_info['total_time']
            
            if process_info['arrival_time']:
                process_info['turnaround_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'COMPLETED'
            process_info['completion_time'] = current_time
            
            self.fcfs_completed_order.insert(0, process_id)
            
            if self.fcfs_current_running == process_id:
                self.fcfs_current_running = None
            
            response_time_str = f"{process_info['response_time']:.2f}s" if process_info['response_time'] is not None else "N/A"
            self.get_logger().info(f"FCFS: Process {process_id} COMPLETED - CPU: {process_info['total_time']:.2f}s, Wait: {process_info['wait_time']:.2f}s, Response: {response_time_str}, TAT: {process_info['turnaround_time']:.2f}s")

    def on_rr_process_scheduled(self, msg):
        process_id = msg.data
        if process_id in self.rr_process_states:
            current_time = time.time()
            
         
            if self.rr_current_running and self.rr_current_running in self.rr_process_states:
                if self.rr_process_states[self.rr_current_running]['state'] == 'RUNNING':
                    prev_process = self.rr_process_states[self.rr_current_running]
                    if prev_process['start_time']:
                        prev_process['total_time'] += current_time - prev_process['start_time']
                   
                    if self.rr_current_running != process_id:
                        self.rr_process_states[self.rr_current_running]['state'] = 'WAITING'
                        self.rr_process_states[self.rr_current_running]['wait_start'] = current_time
                        self.rr_process_states[self.rr_current_running]['preemption_count'] += 1
            
            
            process_info = self.rr_process_states[process_id]
            if process_info['wait_start'] and process_info['state'] == 'WAITING':
                process_info['wait_time'] += current_time - process_info['wait_start']
            
            if process_info['first_execution_time'] is None:
                process_info['first_execution_time'] = current_time
                if process_info['arrival_time']:
                    process_info['response_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'RUNNING'
            process_info['start_time'] = current_time
            self.rr_current_running = process_id
            self.get_logger().info(f"RR: Process {process_id} is now RUNNING (Total wait time: {process_info['wait_time']:.2f}s, Response time: {process_info['response_time']:.2f}s)")

    def on_rr_process_completed(self, msg):
        process_id = msg.data
        if process_id in self.rr_process_states:
            current_time = time.time()
            process_info = self.rr_process_states[process_id]
            
            if process_info['start_time']:
                process_info['total_time'] += current_time - process_info['start_time']
            
            process_info['cpu_burst'] = process_info['total_time']
            
            if process_info['arrival_time']:
                process_info['turnaround_time'] = current_time - process_info['arrival_time']
            
            process_info['state'] = 'COMPLETED'
            process_info['completion_time'] = current_time
            
            self.rr_completed_order.insert(0, process_id)
            
            if self.rr_current_running == process_id:
                self.rr_current_running = None
            
            response_time_str = f"{process_info['response_time']:.2f}s" if process_info['response_time'] is not None else "N/A"
            self.get_logger().info(f"RR: Process {process_id} COMPLETED - CPU: {process_info['total_time']:.2f}s, Wait: {process_info['wait_time']:.2f}s, Response: {response_time_str}, TAT: {process_info['turnaround_time']:.2f}s, Preemptions: {process_info['preemption_count']}")

    def calculate_averages(self, process_states):
        """Calculate average wait time, turnaround time, and response time for completed processes"""
        completed_processes = [info for info in process_states.values() if info['state'] == 'COMPLETED']
        
        if not completed_processes:
            return 0.0, 0.0, 0.0, 0
        
        total_wait_time = sum(process['wait_time'] for process in completed_processes)
        total_turnaround_time = sum(process['turnaround_time'] for process in completed_processes)
        total_response_time = sum(process['response_time'] for process in completed_processes if process['response_time'] is not None)
        
        avg_wait_time = total_wait_time / len(completed_processes)
        avg_turnaround_time = total_turnaround_time / len(completed_processes)
        avg_response_time = total_response_time / len(completed_processes) if completed_processes else 0.0
        
        return avg_wait_time, avg_turnaround_time, avg_response_time, len(completed_processes)

    def update_display(self):
        marker_array = MarkerArray()
        
        delete_marker = Marker()
        delete_marker.header.frame_id = "map"
        delete_marker.header.stamp = self.get_clock().now().to_msg()
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)
        
        title_marker = self.create_text_marker(
            0, "CPU Scheduling Comparison: FCFS vs Round Robin vs Priority", 
            0.0, 11.0, 1.0, 1.0, 1.0, 1.0, 1.0  # White, large text
        )
        marker_array.markers.append(title_marker)
        
        marker_id = 1
        
        fcfs_title = self.create_text_marker(
            marker_id, "FIRST COME FIRST SERVE (FCFS)", 
            -18.0, 9.0, 0.7, 0.0, 1.0, 1.0, 1.0  # Cyan
        )
        marker_array.markers.append(fcfs_title)
        marker_id += 1
        
        fcfs_avg_wait, fcfs_avg_turnaround, fcfs_avg_response, fcfs_completed = self.calculate_averages(self.fcfs_process_states)
        if fcfs_completed > 0:
            fcfs_stats = self.create_text_marker(
                marker_id, f"Stats (n={fcfs_completed}) | Avg Wait: {fcfs_avg_wait:.2f}s | Avg Response: {fcfs_avg_response:.2f}s | Avg TAT: {fcfs_avg_turnaround:.2f}s", 
                -18.0, 8.4, 0.35, 0.0, 1.0, 1.0, 1.0
            )
            marker_array.markers.append(fcfs_stats)
            marker_id += 1
        
        marker_id = self.display_scheduler_processes(marker_array, self.fcfs_process_states, 
                                                self.fcfs_current_running, self.fcfs_completed_order,
                                                -18.0, 7.8, marker_id, "FCFS")
        
        rr_title = self.create_text_marker(
            marker_id, "ROUND ROBIN (RR)", 
            0.0, 9.0, 0.7, 1.0, 0.0, 1.0, 1.0  # Magenta
        )
        marker_array.markers.append(rr_title)
        marker_id += 1
        
        rr_avg_wait, rr_avg_turnaround, rr_avg_response, rr_completed = self.calculate_averages(self.rr_process_states)
        if rr_completed > 0:
            rr_stats = self.create_text_marker(
                marker_id, f"Stats (n={rr_completed}) | Avg Wait: {rr_avg_wait:.2f}s | Avg Response: {rr_avg_response:.2f}s | Avg TAT: {rr_avg_turnaround:.2f}s", 
                0.0, 8.4, 0.35, 1.0, 0.0, 1.0, 1.0
            )
            marker_array.markers.append(rr_stats)
            marker_id += 1
        
        marker_id = self.display_scheduler_processes(marker_array, self.rr_process_states, 
                                                self.rr_current_running, self.rr_completed_order,
                                                0.0, 7.8, marker_id, "RR")
        
        priority_title = self.create_text_marker(
            marker_id, "PRIORITY SCHEDULING", 
            18.0, 9.0, 0.7, 1.0, 1.0, 0.0, 1.0  
        )
        marker_array.markers.append(priority_title)
        marker_id += 1
        
        priority_avg_wait, priority_avg_turnaround, priority_avg_response, priority_completed = self.calculate_averages(self.priority_process_states)
        if priority_completed > 0:
            priority_stats = self.create_text_marker(
                marker_id, f"Stats (n={priority_completed}) | Avg Wait: {priority_avg_wait:.2f}s | Avg Response: {priority_avg_response:.2f}s | Avg TAT: {priority_avg_turnaround:.2f}s", 
                18.0, 8.4, 0.35, 1.0, 1.0, 0.0, 1.0
            )
            marker_array.markers.append(priority_stats)
            marker_id += 1
        
        marker_id = self.display_scheduler_processes(marker_array, self.priority_process_states, 
                                                self.priority_current_running, self.priority_completed_order,
                                                18.0, 7.8, marker_id, "Priority")
        
        if fcfs_completed > 0 or rr_completed > 0 or priority_completed > 0:
            comparison_title = self.create_text_marker(
                marker_id, "PERFORMANCE COMPARISON", 
                0.0, -3.0, 0.8, 1.0, 0.5, 0.0, 1.0 
            )
            marker_array.markers.append(comparison_title)
            marker_id += 1
            
            schedulers = []
            if fcfs_completed > 0:
                schedulers.append(("FCFS", fcfs_avg_wait, fcfs_avg_turnaround, fcfs_avg_response))
            if rr_completed > 0:
                schedulers.append(("RR", rr_avg_wait, rr_avg_turnaround, rr_avg_response))
            if priority_completed > 0:
                schedulers.append(("Priority", priority_avg_wait, priority_avg_turnaround, priority_avg_response))
            
            if len(schedulers) > 1:
                # Best wait time
                best_wait = min(schedulers, key=lambda x: x[1])
                wait_comp_text = f"Best Avg Wait Time: {best_wait[0]} ({best_wait[1]:.2f}s)"
                wait_comp_marker = self.create_text_marker(
                    marker_id, wait_comp_text, 
                    0.0, -3.6, 0.5, 0.0, 1.0, 0.0, 1.0  
                )
                marker_array.markers.append(wait_comp_marker)
                marker_id += 1
                
                best_response = min(schedulers, key=lambda x: x[3])
                response_comp_text = f"Best Avg Response Time: {best_response[0]} ({best_response[3]:.2f}s)"
                response_comp_marker = self.create_text_marker(
                    marker_id, response_comp_text, 
                    0.0, -4.1, 0.5, 0.0, 1.0, 0.0, 1.0 
                )
                marker_array.markers.append(response_comp_marker)
                marker_id += 1
                
                best_tat = min(schedulers, key=lambda x: x[2])
                tat_comp_text = f"Best Avg Turnaround: {best_tat[0]} ({best_tat[2]:.2f}s)"
                tat_comp_marker = self.create_text_marker(
                    marker_id, tat_comp_text, 
                    0.0, -4.6, 0.5, 0.0, 1.0, 0.0, 1.0  
                )
                marker_array.markers.append(tat_comp_marker)
                marker_id += 1
        
      
        self.marker_publisher.publish(marker_array)
        

    def display_scheduler_processes(self, marker_array, process_states, current_running, completed_order, x_offset, y_start, marker_id, scheduler_name):
        """Display processes for a specific scheduler with most recent completed first"""
        current_time = time.time()
        
        sorted_processes = []
        
        if current_running and current_running in process_states:
            sorted_processes.append((current_running, process_states[current_running]))
        
        for process_id, info in process_states.items():
            if info['state'] == 'WAITING':
                sorted_processes.append((process_id, info))
        
        for process_id in completed_order[:6]:  
            if process_id in process_states:
                sorted_processes.append((process_id, process_states[process_id]))
        
        row_height = 0.35
        max_display = 10  
        
        for idx, (process_id, info) in enumerate(sorted_processes[:max_display]):
            state = info['state']
            
            if state == 'WAITING':
                if info['wait_start']:
                    current_wait = current_time - info['wait_start']
                    total_wait = info['wait_time'] + current_wait
                else:
                    total_wait = info['wait_time']
                time_display = f"Wait: {total_wait:.1f}s"
                color = (1.0, 1.0, 0.0, 1.0)  # Yellow
                
                if scheduler_name == "Priority" and 'priority' in info:
                    original_priority = self.original_priorities.get(process_id, info['priority'])
                    current_priority = info['priority']
                    if original_priority != current_priority:
                        priority_display = f"P:{original_priority:.1f}:{current_priority:.1f}"
                    else:
                        priority_display = f"P:{current_priority:.1f}"
                    process_text = f"{process_id} ({priority_display}): WAITING ({time_display})"
                else:
                    process_text = f"{process_id}: WAITING ({time_display})"
                    
            elif state == 'RUNNING':
                run_time = current_time - info['start_time'] if info['start_time'] else 0
                total_time = info['total_time'] + run_time
                time_display = f"CPU: {total_time:.1f}s"
                color = (0.0, 1.0, 0.0, 1.0)  
                
                if scheduler_name == "Priority" and 'priority' in info:
                    original_priority = self.original_priorities.get(process_id, info['priority'])
                    current_priority = info['priority']
                    if original_priority != current_priority:
                        priority_display = f"P:{original_priority:.1f}:{current_priority:.1f}"
                    else:
                        priority_display = f"P:{current_priority:.1f}"
                    process_text = f"{process_id} ({priority_display}): RUNNING ({time_display})"
                else:
                    process_text = f"{process_id}: RUNNING ({time_display})"
                    
            else:  
                cpu_burst = info['cpu_burst'] if info['cpu_burst'] else info['total_time']
                response_time_str = f"{info['response_time']:.1f}s" if info['response_time'] is not None else "N/A"
                time_display = f"CPU: {info['total_time']:.1f}s, Wait: {info['wait_time']:.1f}s, Resp: {response_time_str}, TAT: {info['turnaround_time']:.1f}s"
                color = (1.0, 0.0, 1.0, 1.0)  
                
                if scheduler_name == "Priority" and 'priority' in info:
                    original_priority = self.original_priorities.get(process_id, info['priority'])
                    current_priority = info['priority']
                    if original_priority != current_priority:
                        priority_display = f"P:{original_priority:.1f}:{current_priority:.1f}"
                    else:
                        priority_display = f"P:{current_priority:.1f}"
                    
                    if 'preemption_count' in info:
                        process_text = f"{process_id} ({priority_display},Pr:{info['preemption_count']}): COMPLETED ({time_display})"
                    else:
                        process_text = f"{process_id} ({priority_display}): COMPLETED ({time_display})"
                elif scheduler_name == "RR" and 'preemption_count' in info:
                    process_text = f"{process_id} (B:{cpu_burst:.1f}s,Pr:{info['preemption_count']}): COMPLETED ({time_display})"
                else:
                    process_text = f"{process_id} (Burst: {cpu_burst:.1f}s): COMPLETED ({time_display})"
            
            y_position = y_start - (idx * row_height)
            
            marker = self.create_text_marker(
                marker_id, process_text,
                x_offset, y_position, 0.3,
                color[0], color[1], color[2], color[3]
            )
            marker_array.markers.append(marker)
            marker_id += 1
        
 
        if current_running and current_running in process_states:
            running_info = process_states[current_running]
            current_run_time = current_time - running_info['start_time'] if running_info['start_time'] else 0
            total_cpu_time = running_info['total_time'] + current_run_time
            
            if scheduler_name == "Priority" and 'priority' in running_info:
                original_priority = self.original_priorities.get(current_running, running_info['priority'])
                current_priority = running_info['priority']
                if original_priority != current_priority:
                    priority_display = f"P:{original_priority:.1f}:{current_priority:.1f}"
                else:
                    priority_display = f"P:{current_priority:.1f}"
                cpu_status = f"CPU: Running {current_running}\n({priority_display}, Elapsed: {total_cpu_time:.1f}s)"
            else:
                cpu_status = f"CPU: Running {current_running}\n(Elapsed: {total_cpu_time:.1f}s)"
        else:
            cpu_status = "CPU: IDLE"
        
        cpu_marker = self.create_text_marker(
            marker_id, cpu_status,
            x_offset, y_start - (max_display * row_height) - 0.5, 0.35,
            0.0, 1.0, 1.0, 1.0  
        )
        marker_array.markers.append(cpu_marker)
        marker_id += 1
        
        
        waiting_count = sum(1 for info in process_states.values() if info['state'] == 'WAITING')
        completed_count = sum(1 for info in process_states.values() if info['state'] == 'COMPLETED')
        
        queue_summary = f"Queue: {waiting_count} | Completed: {completed_count}"
        
        queue_marker = self.create_text_marker(
            marker_id, queue_summary,
            x_offset, y_start - (max_display * row_height) - 1.0, 0.35,
            1.0, 0.5, 0.0, 1.0  # Orange
        )
        marker_array.markers.append(queue_marker)
        marker_id += 1
        
        return marker_id

    def create_text_marker(self, marker_id, text, x, y, scale, r, g, b, a):
        marker = Marker()
        marker.header.frame_id = "map"
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.id = marker_id
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD

        marker.pose.position.x = x
        marker.pose.position.y = y
        marker.pose.position.z = 0.0
        marker.pose.orientation.x = 0.0
        marker.pose.orientation.y = 0.0
        marker.pose.orientation.z = 0.0
        marker.pose.orientation.w = 1.0

        
        def adjust_color(r, g, b):
            original = (r, g, b)
            if original == (1.0, 1.0, 0.0):     
                return 1.0, 0.65, 0.0          
            elif original == (1.0, 0.0, 1.0):  
                return 1.0, 0.2, 0.2          
            elif original == (0.0, 1.0, 1.0):   
                return 0.3, 0.8, 1.0            
            elif original == (1.0, 1.0, 0.0):  
                return 1.0, 0.84, 0.0           
            elif original == (1.0, 0.5, 0.0):  
                return 1.0, 0.5, 0.0
            elif original == (1.0, 0.0, 1.0): 
                return 0.87, 0.63, 0.87        
            else:
                return r, g, b 
        adj_r, adj_g, adj_b = adjust_color(r, g, b)

        marker.scale.z = scale
        marker.color.r = adj_r
        marker.color.g = adj_g
        marker.color.b = adj_b
        marker.color.a = a

        marker.text = text
        marker.lifetime = Duration(sec=1, nanosec=0)
        return marker



def main(args=None):
    rclpy.init(args=args)
    node = TripleVisualizationNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Triple Visualization Node shutting down...")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
