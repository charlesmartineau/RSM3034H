"""
Create one parquet file that contains all the headlines for US stocks, last update only, per story ID. Keep relevant columns like derived tickers, etc.
"""
#%%
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

all_files = [f for f in os.listdir(input_directory) if "80001" in f]


# %%
# use polars to loop over the files in input_directory that contains 80001 in the name. Locate the date in format yyyymmdd in the filename and retrieve the ticker from the crsp file.

df_blm = []

for file in tqdm(all_files, desc="Processing Bloomberg News files", unit="file"):
    # extract date from filename
    date_match = re.search(r"_(\d{8})\.parquet$", file)
    date_str = date_match.group(1)
    date = pd.to_datetime(date_str, format="%Y%m%d")

    # read the parquet file
    df = pl.read_parquet(input_directory / file)
    # convert derivedtickers to string
    df = df.with_columns(pl.col("derivedtickers").cast(pl.String))
    # filter df for which derivedtickers is not null
    df = df.filter(pl.col("derivedtickers").is_not_null())
    # keep language_string == "EN"
    df = df.filter(pl.col("language_string") == "ENGLISH")

    # convert the capture_time column that is in UTC to EST time
    df = df.with_columns(
        pl.col("capture_time").dt.convert_time_zone("America/New_York")
    )

    # convert the capture_time column that is in UTC to EST time
    df = df.with_columns(
        pl.col("time_of_arrival").dt.convert_time_zone("America/New_York")
    )

    # retrieve the unique story_id for which column event=='ADD_1STPASS'
    df_1stpass = df.filter(pl.col("event") == "ADD_1STPASS")
    unique_story_ids = df_1stpass.select("story_id").unique().to_series().to_list()
    # in df, keep only the rows with story_id in unique_story_ids
    if not df_1stpass.is_empty():
        df = df.filter(pl.col("story_id").is_in(unique_story_ids))

    else:
        # the empthy happends for the data 2010-12-07 to 2011-01-11
        df = df.group_by("story_id").first()
        # create a copy
        df_1stpass = df.clone()

    # from df_1stpass merge the capture_time only, first drop capture_time column in df
    # this is because we want the capture_time from the 1st pass event
    df = df.drop("capture_time")
    # then join df_1stpass on story_id to get the capture_time
    df = df.join(
        df_1stpass.select(["story_id", "capture_time"]), on="story_id", how="left"
    )

    # create a date column in the format YYYY-MM-DD from capture_time
    df = df.with_columns(pl.col("capture_time").dt.strftime("%Y-%m-%d").alias("date"))

    # by story_id, keep the last row using polar's groupby and last
    # essentially, we are capturing the last update (in case some tickers are added later in event==UPDATES)
    df = df.group_by(["date", "story_id"]).last()

    # because of the UTC to EST, an article can show up in two different dates, we need to keep the one with the first entry.
    df = df.group_by("story_id").first()

    # keep the columns: story_id, derivedtickers, event, language_string, headline, body_text
    df = df.select(
        ["date", "time_of_arrival", "capture_time", "story_id", "derivedtickers", "derivedtickers_scores", "derivedtopics", "hot_level", "headline"]
    )

    # append to df_blm
    df_blm.append(df)

# concatenate all the dataframes in df_blm
df_blm = pl.concat(df_blm)

df_blm = df_blm.group_by(["story_id"]).last()

df_blm.write_parquet(output_dir / "bloomberg_combining_english_headlines_files.parquet")
