# Bharat.Law — Mini Legal Data Pipeline (Assignment Submission)

An end-to-end reproducible pipeline that:
**Crawls → Normalizes → Chunks → Extracts Legal Entities (NER) → (Evaluates)**

---

## Features Delivered

| Stage | Description |
|-------|-------------|
| Crawler | Ethical BFS crawling with robots.txt compliance, retry logic, JS-domain whitelist |
| Parser | Converts HTML/PDF → Markdown using Readability-lxml + PyMuPDF |
| Chunker | 400–800 token chunks with ~80 token overlap using headings |
| NER | Hybrid Legal NER: Regex + spaCy ORG detection |
| Evaluation | Exact-span F1 score if gold dataset available |

---

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm || true
python -m playwright install chromium || true

# Run pipeline
python main.py --seed data/seed_urls.json --max-pages 10 --depth 2 --delay 1.0 --eval