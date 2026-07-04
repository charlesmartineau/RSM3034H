#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_parquet("/Users/charles.martineau/Dropbox/Teaching/Rotman/RSM3034H/data/clean/event_earnings_data_20260514_012508.parquet")

# %%
df.head()
# %%
df = pd.read_parquet("/Users/charles.martineau/Dropbox/Teaching/Rotman/RSM3034H/data/restricted/iclink.parquet")
# %%
