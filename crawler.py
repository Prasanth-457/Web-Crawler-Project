from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

from models import get_connection

HEADERS = {
    "User-Agent": "AdvancedWebCrawler/1.0 (Educational Flask Project)"
}


class WebCrawler:
    def __init__(self, run_id, max_pages=10, same_domain=True):
        self.run_id = run_id
        self.max_pages = max_pages
        self.same_domain = same_domain
        self.visited = set()
        self.saved_links = set()

    def save_page(self, url, title, meta_description, status_code, content_type):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO pages
            (run_id, url, title, meta_description, status_code, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.run_id, url, title, meta_description, status_code, content_type),
        )
        conn.commit()
        conn.close()

    def save_link(self, source_url, target_url):
        key = (source_url, target_url)
        if key in self.saved_links:
            return

        self.saved_links.add(key)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO links (run_id, source_url, target_url)
            VALUES (?, ?, ?)
            """,
            (self.run_id, source_url, target_url),
        )
        conn.commit()
        conn.close()

    def normalize_url(self, base_url, href):
        absolute = urljoin(base_url, href)
        absolute, _ = urldefrag(absolute)
        return absolute.rstrip("/")

    def allowed_url(self, seed_domain, target_url):
        if not self.same_domain:
            return True
        return urlparse(target_url).netloc == seed_domain

    def crawl(self, seed_url):
        queue = deque([seed_url.rstrip("/")])
        seed_domain = urlparse(seed_url).netloc
        crawled_count = 0

        while queue and crawled_count < self.max_pages:
            current_url = queue.popleft()

            if current_url in self.visited:
                continue

            self.visited.add(current_url)

            try:
                response = requests.get(current_url, headers=HEADERS, timeout=6)
                content_type = response.headers.get("Content-Type", "unknown")

                if "text/html" not in content_type:
                    self.save_page(
                        current_url,
                        "Non-HTML Resource",
                        "Skipped because content is not HTML",
                        response.status_code,
                        content_type,
                    )
                    crawled_count += 1
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                title = (
                    soup.title.string.strip()
                    if soup.title and soup.title.string
                    else "No Title"
                )

                meta_tag = soup.find("meta", attrs={"name": "description"})
                meta_description = (
                    meta_tag.get("content", "").strip()
                    if meta_tag
                    else "No Description"
                )

                self.save_page(
                    current_url,
                    title,
                    meta_description,
                    response.status_code,
                    content_type,
                )
                crawled_count += 1

                for anchor in soup.find_all("a", href=True):
                    href = anchor["href"].strip()

                    if href.startswith("javascript:") or href.startswith("mailto:"):
                        continue

                    next_url = self.normalize_url(current_url, href)

                    if not next_url.startswith("http"):
                        continue

                    if self.allowed_url(seed_domain, next_url):
                        self.save_link(current_url, next_url)
                        if next_url not in self.visited:
                            queue.append(next_url)

            except requests.RequestException:
                self.save_page(
                    current_url,
                    "Failed to Fetch",
                    "Request error occurred while crawling the page",
                    0,
                    "unknown",
                )
                crawled_count += 1

        return crawled_count