import redis
from config.settings import REDIS_URI

class RedisQueue:
    def __init__(self):
        self.client = redis.Redis.from_url(REDIS_URI, decode_responses=True)
        self.queue_key = "crawler:queue"
        self.visited_key = "crawler:visited"

    def is_visited(self, url):
        return self.client.sismember(self.visited_key, url)

    def mark_visited(self, url):
        self.client.sadd(self.visited_key, url)

    def enqueue(self, url, priority=0):
        # We use a sorted set. A lower score means it gets popped first by zpopmin
        if not self.is_visited(url):
            self.client.zadd(self.queue_key, {url: -priority})
            return True
        return False

    def dequeue(self):
        # Pop the URL with the lowest score (highest priority)
        result = self.client.zpopmin(self.queue_key, count=1)
        if result:
            url, _ = result[0]
            # When dequeued, we immediately mark it as visited to prevent duplicate works
            self.mark_visited(url)
            return url
        return None

    def get_queue_size(self):
        return self.client.zcard(self.queue_key)

    def get_visited_count(self):
        return self.client.scard(self.visited_key)

    def clear(self):
        """Clear the queue and visited set"""
        self.client.delete(self.queue_key, self.visited_key)
