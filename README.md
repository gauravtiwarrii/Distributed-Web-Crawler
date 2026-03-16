# 🕸️ Distributed Web Crawler

A scalable, distributed web crawler built with Python, Redis, and MongoDB. This system is designed to efficiently scrape web pages concurrently using multiple worker threads, parse HTML content, and store the extracted data and links for further processing.

It features a real-time Streamlit dashboard to monitor crawling metrics and progress.

---

## 🚀 Features

*   **Distributed Architecture**: Uses Redis as a centralized URL queue and visited set to distribute work across multiple crawler workers.
*   **Multithreaded Workers**: Workers can run concurrently (using standard threads or distributed across machines).
*   **Politeness & Rules**: 
    *   Respects `robots.txt` rules using standard Python parsers.
    *   Implements domain-based rate limiting to avoid overwhelming target servers.
*   **HTML Parsing & Link Extraction**: Uses `BeautifulSoup` to scrape titles, meta descriptions, content, and internal/external links.
*   **Persistent Storage**: Saves scraped page data into MongoDB.
*   **Real-time Dashboard**: Streamlit-based web interface to track:
    *   Total pages crawled
    *   Current queue size
    *   Active known URLs
    *   Live feed of recently parsed pages and link counts

---

## ⚙️ Architecture & Data Flow

### 🔍 How It Works (Step-by-Step)

1. **Seeding Phase**: A user adds one or more starting URLs (seeds) to the Redis queue using `main.py --seed`.
2. **Worker Activation**: Multiple worker threads are spawned via `main.py --worker`. They each continuously listen to the Redis queue for new URLs.
3. **Dequeue & Validate**: A worker pulls a URL. It first checks if the URL has already been visited (using Redis sets). If not, it proceeds.
4. **Politeness Check**: The worker checks the target domain's `robots.txt` rules and enforces a standard `CRAWL_DELAY` (rate limit) to ensure the server isn't overloaded.
5. **Fetching & Parsing**: The worker makes an HTTP GET request. The HTML response is passed to `BeautifulSoup` to extract the page title, meta description, readable text content, and all hyperlinks (both internal and external).
6. **Data Storage**: The parsed text data is saved as a document in the MongoDB `pages` collection.
7. **Queueing New Links**: All newly discovered hyperlinks extracted from the page are pushed back into the Redis queue at a lower priority to be eventually crawled by other workers. 
8. **Repeat**: The cycle continues infinitely as long as there are URLs in the queue.

### System Flowchart

```mermaid
graph TD
    subgraph Initialization
    A[User/Admin] -->|Seed URLs| B(main.py --seed)
    B --> C[(Redis: URL Queue)]
    end

    subgraph Crawler Worker Nodes
    W1[Worker Thread 1]
    W2[Worker Thread X]
    end

    subgraph Data Flow
    C -.->|Dequeue URL| W1
    C -.->|Dequeue URL| W2
    
    W1 -->|1. Check robots.txt & Rate Limit| S[Scheduler]
    W2 -->|1. Check robots.txt & Rate Limit| S
    
    S -->|2. HTTP GET| Web[Target Website]
    Web -->|3. HTML Response| P[HTML Parser]
    
    P -->|4. Extracted Links| C
    P -->|5. Parsed Content| DB[(MongoDB: Pages)]
    end

    subgraph Monitoring
    DB -.->|Read Metrics| D[Streamlit Dashboard]
    C -.->|Read Queue Size| D
    end
```

---

## 🛠️ Prerequisites

*   **Docker Desktop** (for spinning up Redis and MongoDB containers)
*   **Python 3.8+** (Tested on Python 3.13)

---

## 💻 Installation & Setup

### 1. Start the Database Services
Use Docker Compose to spin up the local Redis server (for the queue) and MongoDB server (for storage).

```bash
docker compose up -d
```

### 2. Set up the Python Environment
Create a virtual environment and install the required dependencies.

```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install streamlit pandas # Required for the dashboard
```

### 3. Configure the Environment
Ensure you have a `.env` file in the root directory pointing to the local Docker services.
```env
REDIS_URI=redis://localhost:6379/0
MONGO_URI=mongodb://root:example@localhost:27017/
MAX_WORKER_THREADS=5
CRAWL_DELAY=1.0
USER_AGENT=DistributedWebCrawler/1.0
```

---

## 🏃‍♂️ Running the Crawler

The crawler runs via the `main.py` entry point. 

### Seed the Queue
Before workers can crawl, you must add initial seed URLs.

```bash
python main.py --seed "https://example.com"
```

### Start the Workers
Start the crawler workers to begin dequeuing and parsing URLs.

```bash
python main.py --worker --threads 5
```

### Clear the Queue (Reset)
If you need to wipe the Redis queue and start over:

```bash
python main.py --clear
```

---

## 📊 Viewing the Dashboard

To view the live Streamlit dashboard showing crawler statistics:

```bash
streamlit run dashboard/app.py
```

The UI will automatically open in your browser at `http://localhost:8501`.
