import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MAX_WORKER_THREADS = int(os.getenv("MAX_WORKER_THREADS", "10"))
CRAWL_DELAY_SECONDS = float(os.getenv("CRAWL_DELAY_SECONDS", "1.0"))
