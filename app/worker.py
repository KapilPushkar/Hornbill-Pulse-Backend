import threading
import queue
import asyncio
import os
import platform
import psutil
import time
from concurrent.futures import ThreadPoolExecutor

worker_loop = None

def set_low_priority():
    try:
        process = psutil.Process()
        if platform.system() == 'Windows':
            process.nice(psutil.IDLE_PRIORITY_CLASS)
            cpu_count = psutil.cpu_count()
            usable_cpus = list(range(max(1, cpu_count // 4)))
            process.cpu_affinity(usable_cpus)
        else:
            os.nice(19)
    except Exception as e:
        print(f"Warning: Could not set priority: {e}")

class ResourceLimitedWorker:
    def __init__(self, cpu_percent=25):
        self.cpu_percent = cpu_percent
        self.process = psutil.Process()
        self.running = True
        
    async def check_resources(self):
        while self.running:
            try:
                cpu_percent = self.process.cpu_percent(interval=0.1)
                if cpu_percent > self.cpu_percent:
                    await asyncio.sleep(0.5)
                
                mem = psutil.virtual_memory()
                if mem.percent > 75:
                    await asyncio.sleep(1.0)
                    
                await asyncio.sleep(0.1)
            except Exception:
                await asyncio.sleep(0.1)

    async def run_task_with_limits(self, task):
        monitor_task = asyncio.create_task(self.check_resources())
        try:
            await task()
        finally:
            self.running = False
            await monitor_task

def worker():
    global worker_loop
    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)
    
    set_low_priority()
    resource_worker = ResourceLimitedWorker()
    
    while True:
        try:
            task = task_queue.get()
            if task is None:
                break
            
            worker_loop.run_until_complete(
                resource_worker.run_task_with_limits(task)
            )
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Task error: {e}")
        finally:
            task_queue.task_done()
            resource_worker = ResourceLimitedWorker()
    
    worker_loop.close()

task_queue = queue.Queue()
thread_pool = ThreadPoolExecutor(max_workers=1)

worker_thread = threading.Thread(target=worker, name="LowPriorityWorker")
worker_thread.daemon = True
worker_thread.start()

def add_task(task):
    task_queue.put(task)

def shutdown():
    add_task(None)
    worker_thread.join()
    thread_pool.shutdown()
