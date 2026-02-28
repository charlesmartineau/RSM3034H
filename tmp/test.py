#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

df = pd.read_parquet("/Users/charles.martineau/Dropbox/Teaching/Rotman/RSM3034H/data/clean/panel_data_20260202_025510.parquet")

# %%
compu = pd.read_parquet("/Users/charles.martineau/Dropbox/Teaching/Rotman/RSM3034H/data/download_cache/compustat_annual_20260228_031324.parquet")
# %%
