import streamlit as st
import pandas as pd
import time
from pymongo import MongoClient
import redis
import sys
import os
import subprocess

# Ensure config can be imported securely
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import MONGO_URI, REDIS_URI
from crawler_queue.redis_queue import RedisQueue

# --- Initialization ---
st.set_page_config(
    page_title="Crawler Dashboard", 
    page_icon="🕸️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better aesthetics
st.markdown("""
<style>
    .stMetric {
        background-color: rgba(28, 131, 225, 0.1);
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1c83e1;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        text-align: center;
        font-weight: bold;
    }
    .running { background-color: rgba(46, 204, 113, 0.2); border: 1px solid #2ecc71; color: #2ecc71; }
    .stopped { background-color: rgba(231, 76, 60, 0.2); border: 1px solid #e74c3c; color: #e74c3c; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_db_client():
    return MongoClient(MONGO_URI)

@st.cache_resource
def get_redis_client():
    return redis.Redis.from_url(REDIS_URI, decode_responses=True)

client = get_db_client()
db = client['crawler_db']
pages_collection = db['pages']

r = get_redis_client()

st.title("🕸️ Distributed Web Crawler Dashboard")

# --- UI for Seeding URLs ---
st.sidebar.header("🌱 Seed URLs")
st.sidebar.markdown("Enter a new URL to add it to the crawler queue.")

with st.sidebar.form(key='seed_form', clear_on_submit=True):
    seed_input = st.text_input("URL to Crawl", placeholder="https://example.com")
    submit_button = st.form_submit_button(label="Add to Queue")
    
    if submit_button and seed_input:
        if seed_input.startswith("http://") or seed_input.startswith("https://"):
            queue = RedisQueue()
            queue.enqueue(seed_input.strip(), priority=10)
            st.sidebar.success(f"Added {seed_input} to queue!")
        else:
            st.sidebar.error("Please enter a valid URL starting with http:// or https://")

st.sidebar.markdown("---")

# --- UI for Worker Control ---
st.sidebar.header("⚙️ Worker Control")

# Initialize session state for the worker process if it doesn't exist
if 'worker_process' not in st.session_state:
    st.session_state.worker_process = None

worker_threads = st.sidebar.number_input("Threads", min_value=1, max_value=20, value=5)

col_start, col_stop = st.sidebar.columns(2)

if col_start.button("▶️ Start", use_container_width=True):
    if st.session_state.worker_process is None or st.session_state.worker_process.poll() is not None:
        # Start the worker process in the background
        # Use python executable from the current environment
        cmd = [sys.executable, "main.py", "--worker", "--threads", str(worker_threads)]
        try:
            # We explicitly pass the cwd to the project root
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            st.session_state.worker_process = subprocess.Popen(
                cmd, 
                cwd=root_dir,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            st.sidebar.success(f"Started {worker_threads} workers!")
        except Exception as e:
            st.sidebar.error(f"Failed to start workers: {e}")
    else:
        st.sidebar.warning("Workers are already running.")

if col_stop.button("⏹️ Stop", use_container_width=True):
    if st.session_state.worker_process is not None and st.session_state.worker_process.poll() is None:
        st.session_state.worker_process.terminate()
        st.session_state.worker_process = None
        st.sidebar.success("Workers stopped.")
    else:
        st.sidebar.info("No active workers.")
        
# Display status using custom HTML
if st.session_state.worker_process is not None and st.session_state.worker_process.poll() is None:
    st.sidebar.markdown('<div class="status-box running">🟢 WORKERS RUNNING</div>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<div class="status-box stopped">🔴 WORKERS STOPPED</div>', unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown("<small>ℹ️ *Metrics auto-refresh every 2 seconds.*</small>", unsafe_allow_html=True)

# --- Track previous metrics for deltas ---
if 'prev_pages' not in st.session_state:
    st.session_state.prev_pages = 0
if 'prev_queue' not in st.session_state:
    st.session_state.prev_queue = 0
if 'prev_visited' not in st.session_state:
    st.session_state.prev_visited = 0

placeholder = st.empty()

with placeholder.container():
    col1, col2, col3 = st.columns(3)
    
    # 1. Pages in DB
    page_count = pages_collection.count_documents({})
    page_delta = page_count - st.session_state.prev_pages
    col1.metric("Total Pages Crawled", f"{page_count:,}", delta=f"{page_delta:,}" if page_delta else None)
    st.session_state.prev_pages = page_count
    
    # 2. Queue Size
    queue_size = r.zcard("crawler:queue")
    queue_delta = queue_size - st.session_state.prev_queue
    col2.metric("URLs Waitlisted", f"{queue_size:,}", delta=f"{queue_delta:,}" if queue_delta else None, delta_color="inverse")
    st.session_state.prev_queue = queue_size
    
    # 3. Visited Set Size
    visited_size = r.scard("crawler:visited")
    visited_delta = visited_size - st.session_state.prev_visited
    col3.metric("Total Known URLs", f"{visited_size:,}", delta=f"{visited_delta:,}" if visited_delta else None)
    st.session_state.prev_visited = visited_size

    if queue_size > 0 and (st.session_state.worker_process is None or st.session_state.worker_process.poll() is not None):
        st.warning("💡 **Tip**: URLs are currently waiting in the queue. Click '▶️ Start' in the sidebar to start crawling!")
        
    st.markdown("---")
    st.subheader("Recent Crawled Pages")

    recent_pages = list(pages_collection.find({}, {"_id": 0, "content": 0}).sort("crawled_at", -1).limit(15))

    if recent_pages:
        df = pd.DataFrame(recent_pages)
        df['links_count'] = df['links'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        
        # Format columns for display
        df['crawled_at'] = pd.to_datetime(df['crawled_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        display_df = df[['title', 'url', 'links_count', 'crawled_at']].rename(columns={
            'title': 'Page Title', 
            'url': 'Crawled URL', 
            'links_count': 'Discovered Links',
            'crawled_at': 'Timestamp (UTC)'
        })
        
        st.dataframe(
            display_df, 
            use_container_width=True,
            column_config={
                "Crawled URL": st.column_config.LinkColumn("Crawled URL", display_text="Open Link ↑")
            },
            hide_index=True
        )
    else:
        st.info("No pages crawled yet. Add a seed URL and start the workers!")

time.sleep(2)
st.rerun()
