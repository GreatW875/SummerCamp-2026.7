import pandas as pd
from pathlib import Path

df = pd.read_csv('/home/xavier/暑期培训/01 python进阶/data/sensor_log.csv')
# print(df)

null_count = df.isnull().sum()
print(f"Null values in each column:\n{null_count}")
df.fillna(51, inplace=True)
null_count = df.isnull().sum()
print(f"Null values in each column:\n{null_count}")
mask = df['value'] > 50

df[mask].to_csv('/home/xavier/暑期培训/01 python进阶/data/sensor_log_50.csv')

# print(df[mask])
