import time
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from config.settings import CRAWL_DELAY_SECONDS

class Scheduler:
    def __init__(self):
        self.robots_cache = {}
        self.domain_last_crawled = {}

    def is_allowed(self, url):
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        if domain not in self.robots_cache:
            rp = RobotFileParser()
            rp.set_url(f"{domain}/robots.txt")
            
            # Use requests with a timeout to fetch robots.txt instead of the blocking rp.read()
            import requests
            import urllib3
            urllib3.disable_warnings()
            try:
                response = requests.get(f"{domain}/robots.txt", timeout=5, verify=False)
                if response.status_code == 200:
                    rp.parse(response.text.splitlines())
            except Exception as e:
                print(f"Failed to fetch robots.txt for {domain}: {e}")
                
            self.robots_cache[domain] = rp

        rp = self.robots_cache[domain]
        # Allow if we couldn't parse robots.txt or it allows the path
        if not rp.default_entry and not rp.entries:
            return True
        return rp.can_fetch("*", url)

    def wait_for_crawl(self, url):
        parsed = urlparse(url)
        domain = parsed.netloc
        
        last_crawled = self.domain_last_crawled.get(domain, 0)
        now = time.time()
        
        elapsed = now - last_crawled
        if elapsed < CRAWL_DELAY_SECONDS:
            time.sleep(CRAWL_DELAY_SECONDS - elapsed)
            
        self.domain_last_crawled[domain] = time.time()
