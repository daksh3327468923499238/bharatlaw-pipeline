
import argparse, os, json, time, sys
from pathlib import Path
from crawler.crawler import Crawler
from parsers.normalize import Normalizer
from chunker.chunker import Chunker
from ner.ner import LegalNER
from scripts.evaluate_ner import evaluate_ner
#this segment load json seed path and provide with url values without keys
#produces simple list for crawler
def load_seed(seed_path):
    with open(seed_path,'r') as f:
        return list(json.load(f).values())

def main():
    #creating command pipeline
    #this parser gives gives you access to your code
    p=argparse.ArgumentParser()
    #giving statrting web to crawler
    p.add_argument('--seed',default='data/seed_urls.json')
    #defines the pages for crawler
    p.add_argument('--max-pages',type=int,default=15)
    #defining depth of webpage for crawler
    p.add_argument('--depth',type=int,default=3)
    #defining delay for ethical crawling
    p.add_argument('--delay', type=float,default=1.0)
    #stating that argument can take multiple values
    p.add_argument('--js-domains',nargs='*',default='nujslawreview.org')
    #enables evaluation mode
    p.add_argument('--eval',action='store_true')
    #now passing all th arguement
    args=p.parse_args()
    #loading seeds
    seed_urls=load_seed(args.seed)
    #using current directory as the pipeline
    out=Path('.')

    # Crawl initialisation
    #out stores the current project directory
    #js-domain,max pages, delay, depth is converted into a set
    crawler = Crawler(out_dir=out, js_domains=set(args.js_domains), polite_delay=args.delay, max_depth=args.depth, max_pages=args.max_pages)
    #this lines actually starts crawler
    crawled_count = crawler.run(seed_urls=seed_urls)

    #normaliser
    #post crawler class for clean and standardise meaningful text and meta data
    #base_dir=out suggest which files to normalise
    normalizer = Normalizer(base_dir=out)
    #runs normaliser
    norm_count = normalizer.run()

    # Chunking initialisation
    #base_dir=out suggest which file to chunks\
    chunker = Chunker(base_dir=out)
    #runs chunking
    chunk_stats = chunker.run()
    

    #Named Entity recognition
    #detecting specific legality in text
    #LegalNER is our custom hybrid ner engine
    #combines patter and ml extraction
    ner = LegalNER(base_dir=out)
    #running NER
    ner_path = ner.run()

    #evaluation
    f1_line = ""
    gold = out / 'data' / 'gold_ner.jsonl'
    if args.eval and gold.exists():
        metrics = evaluate_ner(gold_path=str(gold), pred_path=str(ner_path))
        f1_line = f"\nNER F1-score: {metrics['f1']:.2f}"

    # Final summary
    print("Pipeline Summary: ")
    print(f"Pages crawled: {crawled_count}")
    print(f"Normalized docs: {norm_count}")
    print(f"Chunks created: {chunk_stats['chunks']}")
    print(f"Avg tokens/chunk: {chunk_stats['avg_tokens']:.0f}" + f"{f1_line}")

if __name__ == '__main__':
    main()
