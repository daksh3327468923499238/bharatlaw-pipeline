\
import json, os, re
from pathlib import Path
import fitz  # PyMuPDF
#UnicodeDammit decodes bytes to str
from bs4 import BeautifulSoup, UnicodeDammit
from readability.readability import Document
#takes json as input which is json lines
def read_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        #iterates one line at a time
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)
#parsing html
def to_markdown_html(html_bytes: bytes, url: str) -> str:
    # Convert bytes to unicode (detect encoding robustly)
    try:
        html_str = UnicodeDammit(html_bytes, is_html=True).unicode_markup
    except Exception:
        html_str = html_bytes.decode("utf-8", errors="replace")

    # Extract main content (readability wants str, NOT bytes)
    try:
        doc = Document(html_str)
        html_main = doc.summary(html_partial=True)  # keep as str
    except Exception:
        html_main = html_str  # graceful fallback

    # Parse and strip junk
    soup = BeautifulSoup(html_main, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    md_lines = []
    title = soup.title.get_text(strip=True) if soup.title else url
    md_lines.append(f"# {title}")

    for el in soup.find_all(["h1","h2","h3","h4","h5","h6","p","li","pre","code","table"]):
        name = el.name.lower()
        txt = el.get_text(" ", strip=True)
        if not txt:
            continue
        if name.startswith("h"):
            level = int(name[1])
            md_lines.append("#"*level + " " + txt)
        elif name == "li":
            md_lines.append(f"- {txt}")
        else:
            md_lines.append(txt)

    return "\n\n".join(md_lines), title
#parsing pdf
def to_markdown_pdf(pdf_path:Path)->str:
    doc = fitz.open(pdf_path)
    md = [f"# PDF: {pdf_path.name}"]
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text")
        md.append(f"\n\n## Page {i}\n\n{text}")
    return "\n".join(md), f"PDF {pdf_path.name}"

class Normalizer:
    #initialise class
    def __init__(self, base_dir:Path):
        self.base_dir = Path(base_dir)
        self.idx_in = self.base_dir/"crawl_index.jsonl"
        self.norm_dir = self.base_dir/"normalized"
        self.norm_dir.mkdir(exist_ok=True, parents=True)
        self.norm_idx = self.base_dir/"normalized_index.jsonl"
        #stores the data
    def _write_index_row(self, row:dict):
        with open(self.norm_idx, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
#running 
    def run(self)->int:
        count = 0
        for row in read_jsonl(self.idx_in):
            url = row["url"]; urlh = row["url_hash"]
            raw_path = Path(row["path_to_raw"])
            source_type = "pdf" if raw_path.suffix.lower()==".pdf" else "html"
            if source_type == "html":
                with open(raw_path, "rb") as f:
                    html = f.read()
                md_text, title = to_markdown_html(html, url)
            else:
                md_text, title = to_markdown_pdf(raw_path)

            out_md = self.norm_dir / f"{urlh}.md"
            with open(out_md, "w", encoding="utf-8") as f:
                f.write(md_text)

            self._write_index_row({
                "url": url,
                "url_hash": urlh,
                "source_type": source_type,
                "title": title,
                "detected_language": "en",
                "char_count": len(md_text),
                "path_to_text": str(out_md)
            })
            count += 1
        return count
