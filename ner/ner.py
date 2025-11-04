\
import re, json
from pathlib import Path
#pattern for common legal document
SECTION_RE = re.compile(r'\b(?:section|sec\.?)\s+\d+[A-Za-z]?(?:\(\d+\))*[A-Za-z]?(?:\([\da-zA-Z]+\))*', re.IGNORECASE)
ORDER_RULE_RE = re.compile(r'\bOrder\s+[IVXLC]+(?:\s+Rule\s+\d+)?', re.IGNORECASE)
DATE_RE = re.compile(r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t\.|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b')
MONEY_RE = re.compile(r'(?:₹|Rs\.?\s*|INR\s*)\d{1,3}(?:[,\d]{0,12})(?:\.\d+)?|\b(?:USD|EUR|GBP)\s*\d{1,3}(?:[,\d]{0,12})(?:\.\d+)?', re.IGNORECASE)
ACT_RE = re.compile(r'\b[A-Z][A-Za-z\s]+ Act, \d{4}\b')
#keep running the code without model
def spacy_nlp():
    try:
        import spacy
        return spacy.load("en_core_web_sm")
    except Exception:
        import spacy
        return spacy.blank("en")
#creates any regex into entity schema
def find_iter(pattern, text, label):
    for m in pattern.finditer(text):
        yield {"label": label, "text": m.group(0), "start": m.start(), "end": m.end()}
# LegalNER the custom build model
class LegalNER:
    def __init__(self, base_dir:Path):
        self.base_dir = Path(base_dir)
        self.chunks_path = self.base_dir / "chunks" / "chunks.jsonl"
        self.out_path = self.base_dir / "ner_outputs" / "annotations.jsonl"
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.nlp = spacy_nlp()
#runs all regex and collect entities
    def annotate(self, text):
        ents = []
        # Rule-based
        ents.extend(list(find_iter(SECTION_RE, text, "SECTION_REF")))
        ents.extend(list(find_iter(ORDER_RULE_RE, text, "SECTION_REF")))
        ents.extend(list(find_iter(DATE_RE, text, "DATE")))
        ents.extend(list(find_iter(MONEY_RE, text, "MONEY")))
        # Heuristic Acts
        ents.extend(list(find_iter(ACT_RE, text, "ACT_NAME")))

        # ML
        try:
            doc = self.nlp(text)
            for e in doc.ents:
                if e.label_ == "ORG":
                    ents.append({"label":"ORG","text":e.text,"start":e.start_char,"end":e.end_char})
        except Exception:
            pass

        # Deduplicate overlapping identical spans/labels
        uniq = {(e["label"], e["start"], e["end"]): e for e in ents}
        return list(uniq.values())

    def run(self)->Path:
        with open(self.out_path, "w", encoding="utf-8") as out:
            with open(self.chunks_path, "r", encoding="utf-8") as f:
                for line in f:
                    ch = json.loads(line)
                    text = ch["text"]
                    entities = self.annotate(text)
                    out.write(json.dumps({"chunk_id": ch["chunk_id"], "entities": entities}, ensure_ascii=False) + "\n")
        return self.out_path
