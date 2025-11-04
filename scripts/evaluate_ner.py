\
import json
from pathlib import Path
#loads gold,pred into dicts
def load_ner_jsonl(p):
    data = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            data[row["chunk_id"]] = row["entities"]
    return data

def to_set(entities):
    # Exact match on (label, start, end, text)
    return set((e["label"], e["start"], e["end"], e["text"]) for e in entities)
#creating json file
def evaluate_ner(gold_path: str, pred_path: str):
    gold = load_ner_jsonl(gold_path)
    pred = load_ner_jsonl(pred_path)

    TP = FP = FN = 0
    for chunk_id, gold_ents in gold.items():
        gset = to_set(gold_ents)
        pset = to_set(pred.get(chunk_id, []))
        TP += len(gset & pset)
        FP += len(pset - gset)
        FN += len(gset - pset)

    precision = TP / (TP + FP) if (TP + FP) else 0.0
    recall = TP / (TP + FN) if (TP + FN) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0

    metrics = {"precision": precision, "recall": recall, "f1": f1, "tp": TP, "fp": FP, "fn": FN}
    print(metrics)
    return metrics

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--gold", required=True)
    p.add_argument("--pred", required=True)
    args = p.parse_args()
    evaluate_ner(args.gold, args.pred)
