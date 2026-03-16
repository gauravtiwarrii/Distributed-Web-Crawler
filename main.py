import argparse
import time
import sys
from crawler.worker import CrawlerWorker
from crawler.scheduler import Scheduler
from crawler_queue.redis_queue import RedisQueue
from config.settings import MAX_WORKER_THREADS

def seed_urls(urls):
    queue = RedisQueue()
    for url in urls:
        print(f"Seeding URL: {url}")
        queue.enqueue(url, priority=10) # Seed URLs get high priority
    print(f"Queue size: {queue.get_queue_size()}")

def clear_queue():
    queue = RedisQueue()
    queue.clear()
    print("Queue and visited set cleared.")

def start_workers(num_workers):
    print(f"Starting {num_workers} worker threads...")
    scheduler = Scheduler()
    workers = []
    
    for i in range(num_workers):
        worker = CrawlerWorker(i, scheduler)
        worker.start()
        workers.append(worker)
        
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping workers...")
        for worker in workers:
            worker.stop()
        for worker in workers:
            worker.join()
        print("All workers stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Web Crawler")
    parser.add_argument("--seed", nargs='+', help="Seed URLs to start crawling")
    parser.add_argument("--worker", action="store_true", help="Start worker threads")
    parser.add_argument("--threads", type=int, default=MAX_WORKER_THREADS, help="Number of worker threads")
    parser.add_argument("--clear", action="store_true", help="Clear the Redis queue and visited set")
    
    args = parser.parse_args()
    
    if args.clear:
        clear_queue()
        
    if args.seed:
        seed_urls(args.seed)
        
    if args.worker:
        start_workers(args.threads)
        
    if not (args.clear or args.seed or args.worker):
        parser.print_help()
