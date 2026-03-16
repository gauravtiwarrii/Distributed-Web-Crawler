from pymongo import MongoClient
import datetime
from config.settings import MONGO_URI

class MongoDBStore:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client['crawler_db']
        self.collection = self.db['pages']
        
        # Create an index on URL for fast lookups
        self.collection.create_index("url", unique=True)

    def save_page(self, url, title, meta_desc, content, links):
        page_doc = {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "content": content,
            "links": links,
            "crawled_at": datetime.datetime.utcnow()
        }
        
        try:
            self.collection.update_one(
                {"url": url},
                {"$set": page_doc},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Failed to save page {url}: {e}")
            return False

    def get_page_count(self):
        return self.collection.count_documents({})
    
    def get_recent_pages(self, limit=10):
        return list(self.collection.find({}, {"_id": 0}).sort("crawled_at", -1).limit(limit))
