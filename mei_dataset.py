import os
import pandas as pd

file_name = "leetcode_train.parquet"

if not os.path.exists(file_name):
    print("Downloading for the first time...")
    # Load from web
    df = pd.read_json("hf://datasets/newfacade/LeetCodeDataset/LeetCodeDataset-train.jsonl", lines=True)
    # Save locally as Parquet (much faster and smaller than JSON)
    df.to_parquet(file_name)
else:
    print("Loading from local cache...")
    df = pd.read_parquet(file_name)
    for col in df.columns:
        print(f"{col}: {df[col][0]}")