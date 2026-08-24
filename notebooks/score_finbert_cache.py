"""Score BTC/ETH-relevant headlines with FinBERT; cache to data/cache/ (gitignored)."""

import time

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from src.ingestion.news.history import read_news_history

OUT = "data/cache/finbert_scores.parquet"
SOURCES = ["googlenews_btc", "googlenews_eth", "cointelegraph", "coindesk"]

news = read_news_history()  # ADR-033: monthly partitions, concatenated transparently
rel = news[news["source"].isin(SOURCES)].copy()
titles = rel["title"].astype(str).tolist()
print(f"scoring {len(titles)} headlines with ProsusAI/finbert (CPU)...", flush=True)

tok = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
model.eval()
torch.set_num_threads(4)

# id2label: 0=positive, 1=negative, 2=neutral for ProsusAI/finbert
labels = {i: model.config.id2label[i].lower() for i in range(model.config.num_labels)}
print("labels:", labels, flush=True)
pos_i = next(i for i, l in labels.items() if l == "positive")
neg_i = next(i for i, l in labels.items() if l == "negative")

scores: list[float] = []
BATCH = 64
t0 = time.time()
with torch.no_grad():
    for i in range(0, len(titles), BATCH):
        batch = titles[i : i + BATCH]
        enc = tok(batch, padding=True, truncation=True, max_length=64, return_tensors="pt")
        probs = torch.softmax(model(**enc).logits, dim=-1)
        scores.extend((probs[:, pos_i] - probs[:, neg_i]).tolist())
        if (i // BATCH) % 20 == 0:
            done = i + len(batch)
            rate = done / max(time.time() - t0, 1e-9)
            print(f"  {done}/{len(titles)}  ({rate:.0f}/s)", flush=True)

rel["finbert"] = scores
out = rel[["source", "title", "sentiment", "finbert"]].copy()
out = out.rename(columns={"sentiment": "vader"})
import os
os.makedirs("data/cache", exist_ok=True)
out.to_parquet(OUT)
print(f"DONE: wrote {OUT} ({len(out)} rows) in {time.time()-t0:.0f}s", flush=True)
