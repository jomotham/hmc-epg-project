import pandas as pd

"""
Adds dummy resistance, voltage, current data to a csv without them. Needed for the mosquito models to work at one point.
"""
DATA_PATH = r"Data\Sharpshooter Data - HPR 2017\sharpshooter_labeled\sharpshooter_a01_labeled.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, index_col=0)
length = df['time'].shape[0]
print("Data loaded.")

resistance = pd.Series(9, index=range(length))
voltage = pd.Series(75, index=range(length))
current = pd.Series("DC", index=range(length))

df.insert(0, "resistance", resistance)
df.insert(1, "voltage", voltage)
df.insert(2, "current", current)

print("Writing data...")
df.to_csv("test_sharpshooter.csv")
print(df)
print("Data written.")