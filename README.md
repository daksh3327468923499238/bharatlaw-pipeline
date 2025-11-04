# Bharat.Law — Mini Legal Data Pipeline

An end‑to‑end pipeline that **crawls**, **parses & normalizes**, **chunks**, and runs **NER** on Indian legal web pages.  
One‑command execution via `./run.sh` or `python main.py`.

## Quick start
```bash
git clone <your-fork>
cd bharatlaw-pipeline
./run.sh
# or: python main.py --seed data/seed_urls.json --max-pages 25
```

> Place `gold_ner.jsonl` in `data/` to enable evaluation.

## Design
- **Crawler**: requests (static), optional Playwright for JS, robots.txt respected, retries + backoff, dedupe, depth≤3.
- **Parsing**: HTML→Markdown with headings/lists preserved; PDFs via PyMuPDF with page numbers.
- **Chunking**: 400–800 token target with 50–100 token overlap, split by headings & paragraphs.
- **NER**: hybrid (regex rules for `SECTION_REF`, `DATE`, `MONEY` + spaCy for `ORG`, `ACT_NAME` with heuristics).
- **Eval**: Precision/Recall/F1 against `gold_ner.jsonl` (exact match of label+span).

## Outputs
```
raw/                # raw HTML/PDF
normalized/         # markdown
chunks/             # chunks.jsonl
ner_outputs/        # annotations.jsonl
crawl_index.jsonl
normalized_index.jsonl
```

## Limitations & future work
- JS rendering is domain‑gated to avoid cost; extend `--js-domains` list.
- Evaluation uses exact span match; could add partial/character‑overlap scoring.
- Chunk tokenization uses tiktoken if present; falls back to word-count proxy.
- PDF layout retention is minimal; table preservation is best‑effort.
```

