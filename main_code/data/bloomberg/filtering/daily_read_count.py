# %%
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
from tqdm import tqdm

# %%
# load crsp file
crsp = pl.read_parquet(
    "H:/users_fac/martineau_charles/data/restricted/crsp/crsp_daily.parquet"
)

# %%
input_directory = Path("H:/data_common_master/Bloomberg_News/parquet/")
output_dir = Path(
    "H:/users_fac/martineau_charles/data/restricted/bloomberg_news_aggregation/us/"
)

all_files = [f for f in os.listdir(input_directory) if "80001" in f]


# %%
# use polars to loop over the files in input_directory that contains 80001 in the name. Locate the date in format yyyymmdd in the filename and retrieve the ticker from the crsp file.

df_read = []

for file in tqdm(all_files):
    # extract date from filename
    date_match = re.search(r"_(\d{8})\.parquet$", file)
    date_str = date_match.group(1)
    date = pd.to_datetime(date_str, format="%Y%m%d")
    if date < pd.to_datetime("2015-01-01"):
        continue
    # Retrieve the ticker from the CRSP file by finding unique tickers in the same month
    ticker = list(
        crsp.filter(
            (pl.col("date").dt.year() == date.year)
            & (pl.col("date").dt.month() == date.month)
        )
        .select("ticker")
        .to_series()
    )
    ticker = np.unique(ticker)
    # read the parquet file
    df = pl.read_parquet(input_directory / file)
    # convert derivedtickers to string
    df = df.with_columns(pl.col("derivedtickers").cast(pl.String))
    df = df.with_columns(pl.col("derivedtopics").cast(pl.String))

    # filter df for which derivedtickers is not null
    df = df.filter(pl.col("derivedtickers").is_not_null())
    # keep language_string == "EN"
    df = df.filter(pl.col("language_string") == "ENGLISH")

    # possibility: load previous data with story id and filter by that

    # convert the capture_time column that is in UTC to EST time
    df = df.with_columns(
        pl.col("capture_time").dt.convert_time_zone("America/New_York")
    )

    # create a date column in the format YYYY-MM-DD from capture_time
    df = df.with_columns(pl.col("capture_time").dt.strftime("%Y-%m-%d").alias("date"))

    # remove unwanted headlines that contains "QUOTATION RESUMED" and "TRADING RELEASED"
    df = df.filter(
        ~pl.col("headline").str.contains("QUOTATION RESUMED|TRADING RELEASED")
    )

    # in the column derivedtopics, look for topics that include a READ count and exclude those that do not
    df = df.with_columns(pl.col("derivedtopics").str.split("|"))
    # derivedtopics is a list of topics in the column, we want to keep only those that contain "READ", so must loop over the list.
    df = df.filter(pl.col("derivedtopics").list.contains("READ"))

    # by story_id, keep the last row using polar's groupby and last
    # essentially, we are capturing the last update (in case some tickers are added later in event==UPDATES)
    df = df.group_by(["date", "story_id"]).last()

    # loop over columns "derivedtopics" and create new column with the match = re.match(r'READ(\d+)', topic_text)
    df = df.with_columns(
        pl.col("derivedtopics")
        .list.eval(pl.element().str.extract(r"READ(\d+)").cast(pl.Int64))
        .list.max()
        .alias("read_count")
    )

    # remove the rows where read_count is null
    df = df.filter(pl.col("read_count").is_not_null())

    if df.is_empty():
        continue

    # keep the columns: story_id, derivedtickers, event, language_string, headline, body_text
    df = df.select(["date", "story_id", "derivedtickers", "read_count"])
    # column derivedtickers is in this format "AAPL|MSFT|GOOGL", split it by "|" and explode it
    df = df.with_columns(pl.col("derivedtickers").str.split("|"))
    df = df.explode("derivedtickers")
    # drop duplicates using subset story_id and derivedtickers
    df = df.unique(subset=["story_id", "derivedtickers"])
    # keep tickers that shows up in the ticker list
    df = df.filter(pl.col("derivedtickers").is_in(ticker))

    df = df.rename({"derivedtickers": "ticker"})

    # append to df_read
    df_read.append(df)

# concatenate all the dataframes in df_read
df_read = pl.concat(df_read)
df_read = df_read.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))
# sort by date and ticker
df_read = df_read.sort(["date", "ticker"])
# save the dataframe to parquet
df_read.write_parquet(output_dir / "bloomberg_daily_read_count_crsp_ticker.parquet")

df_read = pd.read_parquet(output_dir / "bloomberg_daily_read_count_crsp_ticker.parquet")
df_read["date"] = pd.to_datetime(df_read["date"])
df_read = df_read.sort_values(by=["date", "story_id", "ticker"])

df_read["diff_read_count"] = df_read.groupby(["story_id", "ticker"])[
    "read_count"
].diff()
df_read["diff_read_count"] = np.where(
    df_read["diff_read_count"].isna(), df_read["read_count"], df_read["diff_read_count"]
)

df_read.groupby(["date", "ticker"]).agg(
    {"diff_read_count": "sum"}
).reset_index().to_parquet(
    output_dir / "bloomberg_daily_read_count_crsp_ticker_aggregated.parquet"
)
