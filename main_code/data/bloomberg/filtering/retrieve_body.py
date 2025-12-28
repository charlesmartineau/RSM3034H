# %%
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from tqdm import tqdm


# %%
input_directory = Path("H:/data_common_master/Bloomberg_News/parquet/")
output_dir = Path(
    "H:/users_fac/martineau_charles/data/restricted/bloomberg_news_aggregation/us/"
)

#%%
all_files_body = [f for f in os.listdir(input_directory) if "34151" in f]

# in all files, keep only files for which the date is after 2019
#all_files_body = [
#    f
#    for f in all_files_body
#    if int(re.search(r"_(\d{8})\.parquet$", f).group(1)) >= 20190101
#]

all_files_body = [
    f
    for f in all_files_body
    if (
        (m := re.search(r"_(\d{8})\.parquet$", f)) and
        (20130101 <= int(m.group(1)) < 20190101)
    )
]

#all_files_body = [
#    f
#    for f in all_files_body
#    if (int(re.search(r"_(\d{8})\.parquet$", f).group(1)) < 20130101)
#]

df_headline = pd.read_parquet(
    output_dir / "bloomberg_daily_aggregation_headlines_crsp_ticker.parquet"
)
df_headline['date'] = pd.to_datetime(df_headline['date'])

# create a dataframe that saves the body of the news. To do so, loop over the unique date in df_headline, and retrieve the corresponding dataframe in all_files.
df_body = []
for file in tqdm(all_files_body, desc="Processing Bloomberg News body files", unit="file"):
    # extract date from filename
    date_match = re.search(r"_(\d{8})\.parquet$", file)
    date_str = date_match.group(1)
    date = pd.to_datetime(date_str, format="%Y%m%d")
    story_ids = df_headline[df_headline['date'] == date]['story_id'].unique()

    # read the parquet file and keep only the columns story_id, headline, and body
    df = pl.read_parquet(input_directory / file, columns=["story_id", "event", "headline", "body", "capture_time"])
    df = df.filter(pl.col("event") == "ADD_STORY")
    # remove entries for which the column headline starts with a "*"
    df = df.filter(~pl.col("headline").str.starts_with("*"))
    # convert capture_time to EST
    df = df.with_columns(pl.col("capture_time").dt.convert_time_zone("America/New_York").alias("datetime"))
    
    # keep only the columns: story_id, body_text, date
    df = df.select(["datetime", "story_id", "headline", "body"])

    # keep only the story_id in df that is in df_headline
    df = df.filter(pl.col("story_id").is_in(story_ids))
    
    # append to df_body
    df_body.append(df)

# concatenate all the dataframes in df_body
df_body = pl.concat(df_body)
df_body.write_parquet(
    output_dir / "bloomberg_daily_aggregation_body_crsp_ticker_20130101_20181231.parquet"
)
# %%
