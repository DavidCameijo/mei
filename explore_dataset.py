import os
import pandas as pd

file_name = "leetcode_train.parquet"

df = pd.read_parquet(file_name)

print(df.columns)
print(df.iloc[1])