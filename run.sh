#!/usr/bin/env bash
set -e

# Create venv if needed
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt

# Optional but recommended: install spaCy model & Playwright browser
python -m spacy download en_core_web_sm || true
python -m playwright install chromium || true

# Orchestrate pipeline
python main.py --seed data/seed_urls.json "$@"
