\
import time, hashlib, json, re, os
from urllib.parse import urljoin, urldefrag, urlparse
import requests
#beautifulSoup for link extraction
from bs4 import BeautifulSoup
#for pretty progress bar
from tqdm import tqdm
#for reading robot.txt
import urllib.robotparser as robotparser
from pathlib import Path
#givig name to crawler when it enter the webpage
UA = "BharatLawMiniCrawler/1.0 (+https://example.org)"
#defines folder name where all raw downloaded will be saved
RAW_DIR = "raw"
#this keeps the data of each crawled page
INDEX = "crawl_index.jsonl"
#takes in string and return small hash for string
def hash_url(u:str)->str:
    #build in library for hash
    return hashlib.sha1(u.encode("utf-8")).hexdigest()[:16]
#check small string of url whether it points to a pdf or not
def is_pdf_url(url:str)->bool:
    return url.lower().endswith(".pdf")
#it checks if whether website requires js rendering or not
def should_use_js(url:str, js_domains:set)->bool:
    #buil in library to split url into scheme,domain, path, query
    netloc = urlparse(url).netloc
    return any(netloc.endswith(d) for d in js_domains)

class Crawler:
    #initialisation function
    def __init__(self, out_dir:Path, polite_delay:float=1.0, max_depth:int=3, max_pages:int=25, js_domains:set=None):
        #perform file and directory operation
        self.out_dir = Path(out_dir)
        #stores the delay value 
        self.polite_delay = polite_delay
        #stores how deep is crawler
        self.max_depth = max_depth
        #stores how many max pages
        self.max_pages = max_pages
        #if js domain is provided then use that value otherwise empty set
        self.js_domains = js_domains or set()
        #session keeps cookies, header and connection pooling across multiple request
        self.session = requests.Session()
        #sets up custom user agent header made by session
        self.session.headers.update({"User-Agent": UA})
        #creates path to index file
        self.index_path = self.out_dir / INDEX
        #sub directory
        self.raw_dir = self.out_dir / RAW_DIR
        #ensure it starts saving pages
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        #store urls that are crawled
        self.seen = set()
# this file tells which pages crawler can visit or not
    def _respect_robots(self, base_url):
        rp = robotparser.RobotFileParser()
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            rp.set_url(robots_url)
            rp.read()
        except Exception:
            return True  # be permissive if robots unavailable
        return rp.can_fetch(UA, base_url)
#downloads webpage
    def _fetch(self, url, use_js=False, tries=3):
        backoff = 1.0
        last_exc = None
        for _ in range(tries):
            try:
                if use_js:
                    # Lazy import to avoid heavy dependency if unused
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=True)
                        page = browser.new_page(user_agent=UA)
                        page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        html = page.content()
                        browser.close()
                        return 200, "text/html", html.encode("utf-8"), True
                else:
                    r = self.session.get(url, timeout=30)
                    ctype = r.headers.get("Content-Type","").split(";")[0].strip().lower()
                    return r.status_code, ctype, r.content, False
            except Exception as e:
                last_exc = e
                time.sleep(backoff)
                backoff *= 2
        raise last_exc or RuntimeError("Request failed")
#opens crawl index file with append mode
#to know what was crawled
    def _write_index_row(self, row:dict):
        with open(self.index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
#reutrns integer count if succesfully crawled pages
    def run(self, seed_urls:list)->int:
        #list of tuples (url,depth) for each seed
        queue = [(u, 0) for u in seed_urls]
        count = 0

        pbar = tqdm(total=self.max_pages, desc="Crawling")
        while queue and count < self.max_pages:
            url, depth = queue.pop(0)
            url = urldefrag(url).url  # strip fragments
            if url in self.seen or depth > self.max_depth:
                continue
            self.seen.add(url)
            if not self._respect_robots(url):
                continue

            use_js = should_use_js(url, self.js_domains) and not is_pdf_url(url)
            try:
                status, ctype, content, used_js = self._fetch(url, use_js=use_js)
            except Exception:
                continue

            urlh = hash_url(url)
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            ext = ".pdf" if "pdf" in ctype or is_pdf_url(url) else ".html"
            raw_path = self.raw_dir / f"{urlh}{ext}"
            with open(raw_path, "wb") as f:
                f.write(content)

            self._write_index_row({
                "url": url,
                "status": status,
                "content_type": "application/pdf" if ext==".pdf" else "text/html",
                "used_js": used_js,
                "timestamp": ts,
                "path_to_raw": str(raw_path),
                "url_hash": urlh,
                "depth": depth
            })
            count += 1
            pbar.update(1)

            # Extract and enqueue new links
            if ext == ".html" and status==200:
                try:
                    soup = BeautifulSoup(content, "lxml")
                    for a in soup.select("a[href]"):
                        nxt = urljoin(url, a["href"])
                        if nxt.startswith("mailto:") or nxt.startswith("javascript:"):
                            continue
                        queue.append((nxt, depth+1))
                except Exception:
                    pass

            time.sleep(self.polite_delay)

        pbar.close()
        return count
