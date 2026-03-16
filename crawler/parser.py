from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class HTMLParser:
    @staticmethod
    def parse(html_content, base_url):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        
        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find('meta', attrs={'name': 'description'})
        if meta_tag and meta_tag.get('content'):
            meta_desc = meta_tag['content'].strip()
            
        # Extract text content (remove scripts and styles)
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract links
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if not href:
                continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Simple validation to only keep HTTP/HTTPS links
            parsed_href = urlparse(full_url)
            if parsed_href.scheme in ["http", "https"]:
                # Remove fragment
                clean_url = full_url.split('#')[0]
                links.add(clean_url)
                
        return {
            "title": title,
            "meta_description": meta_desc,
            "content": text,
            "links": list(links)
        }
