\
import json, re
from pathlib import Path
#token estimation by tiktoken
def estimate_tokens(text:str)->int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # rough proxy: ~1 token ≈ 4 chars
        return max(1, len(text)//4)
#reads json file
def read_jsonl(path):
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line=line.strip()
            if line:
                yield json.loads(line)

class Chunker:
    #initialistion
    def __init__(self, base_dir:Path, target_min=400, target_max=800, overlap=80):
        self.base_dir = Path(base_dir)
        self.norm_idx = self.base_dir / "normalized_index.jsonl"
        self.chunks_dir = self.base_dir / "chunks"
        self.chunks_dir.mkdir(parents=True, exist_ok=True)
        self.out_path = self.chunks_dir / "chunks.jsonl"
        self.target_min=target_min; self.target_max=target_max; self.overlap=overlap
#spliting section
    def _split_sections(self, text:str):
        # Split by headings 
        parts = re.split(r'\n(?=# )|\n(?=## )|\n(?=### )', text)
        return [p.strip() for p in parts if p.strip()]
#chunking
    def _chunkify(self, urlhash, url, title, text):
        sections = self._split_sections(text)
        chunks = []
        acc = ""
        section_path = []
        char_cursor = 0
        for sec in sections:
            # Update section path from heading line
            first_line = sec.splitlines()[0]
            if first_line.startswith("#"):
                # Derive a simple breadcrumb from the first heading in the section
                header = first_line.lstrip("# ").strip()
                section_path = [header]
            if acc:
                acc += "\n\n" + sec
            else:
                acc = sec
            tok = estimate_tokens(acc)
            if tok >= self.target_min:
                while tok > self.target_max and "\n\n" in acc:
                    # shrink by removing earliest paragraph
                    first_para_end = acc.find("\n\n")
                    keep = acc[first_para_end+2:]
                    acc = keep
                    tok = estimate_tokens(acc)
                chunk_id = f"{urlhash}:{len(chunks)+1:04d}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "url": url,
                    "title": title,
                    "section_path": section_path,
                    "page_no": None,
                    "char_start": char_cursor,
                    "char_end": char_cursor + len(acc),
                    "token_estimate": tok,
                    "text": acc
                })
                # create overlap
                overlap_tokens = 0
                if "\n\n" in acc:
                    paras = acc.split("\n\n")
                    tail = []
                    while paras and overlap_tokens < self.overlap:
                        tail.insert(0, paras.pop())
                        overlap_tokens = estimate_tokens("\n\n".join(tail))
                    acc = "\n\n".join(tail)
                    char_cursor += len(acc)
                else:
                    acc = ""
                    char_cursor += len(acc)
        # flush
        if acc.strip():
            chunk_id = f"{urlhash}:{len(chunks)+1:04d}"
            chunks.append({
                "chunk_id": chunk_id,
                "url": url,
                "title": title,
                "section_path": section_path,
                "page_no": None,
                "char_start": char_cursor,
                "char_end": char_cursor + len(acc),
                "token_estimate": estimate_tokens(acc),
                "text": acc
            })
        return chunks
#run function
    def run(self):
        total_chunks = 0; total_tokens = 0
        with open(self.out_path, "w", encoding="utf-8") as out:
            for row in read_jsonl(self.norm_idx):
                with open(row["path_to_text"], "r", encoding="utf-8") as f:
                    text = f.read()
                chunks = self._chunkify(row["url_hash"], row["url"], row["title"], text)
                for ch in chunks:
                    out.write(json.dumps(ch, ensure_ascii=False) + "\n")
                total_chunks += len(chunks)
                total_tokens += sum(c["token_estimate"] for c in chunks)
        avg = (total_tokens/total_chunks) if total_chunks else 0
        return {"chunks": total_chunks, "avg_tokens": avg}
