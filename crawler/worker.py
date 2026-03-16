import threading
import requests
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from crawler_queue.redis_queue import RedisQueue
from storage.mongodb_store import MongoDBStore
from crawler.parser import HTMLParser
from crawler.scheduler import Scheduler

class CrawlerWorker(threading.Thread):
    def __init__(self, worker_id, scheduler):
        super().__init__()
        self.worker_id = worker_id
        self.queue = RedisQueue()
        self.store = MongoDBStore()
        self.parser = HTMLParser()
        self.scheduler = scheduler
        self.running = True
        self.daemon = True

    def run(self):
        print(f"Worker {self.worker_id} started")
        
        while self.running:
            url = self.queue.dequeue()
            
            if not url:
                time.sleep(1) # Queue is empty, wait
                continue
                
            print(f"[Worker {self.worker_id}] Crawling: {url}")
            
            # Check Robots.txt
            if not self.scheduler.is_allowed(url):
                print(f"[Worker {self.worker_id}] Blocked by robots.txt: {url}")
                continue
                
            # Rate limiting / Domain politeness
            self.scheduler.wait_for_crawl(url)
            
            try:
                # Fetch page
                headers = {'User-Agent': 'DistributedWebCrawler/1.0'}
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' not in content_type:
                        print(f"[Worker {self.worker_id}] Skipped non-HTML: {url}")
                        continue
                        
                    # Parse HTML
                    parsed_data = self.parser.parse(response.text, url)
                    
                    # Store in DB
                    success = self.store.save_page(
                        url=url,
                        title=parsed_data['title'],
                        meta_desc=parsed_data['meta_description'],
                        content=parsed_data['content'],
                        links=parsed_data['links']
                    )
                    
                    if success:
                        print(f"[Worker {self.worker_id}] Saved: {url} ({len(parsed_data['links'])} links)")
                        
                        # Enqueue new links
                        for link in parsed_data['links']:
                            # Lower priority (0) for generic discovered links
                            self.queue.enqueue(link, priority=0)
                            
                else:
                    print(f"[Worker {self.worker_id}] Failed HTTP {response.status_code}: {url}")
                    
            except requests.RequestException as e:
                 print(f"[Worker {self.worker_id}] Request error {url}: {e}")
            except Exception as e:
                print(f"[Worker {self.worker_id}] Error {url}: {e}")

    def stop(self):
        self.running = False
