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

df_blm = []

df_headline = []

for file in tqdm(all_files, desc="Processing Bloomberg News files", unit="file"):
    # extract date from filename
    date_match = re.search(r"_(\d{8})\.parquet$", file)
    date_str = date_match.group(1)
    date = pd.to_datetime(date_str, format="%Y%m%d")
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

    # check to see if the 1stpass event occured after 4pm, if yes create column post_4pm equal to 1
    df_1stpass = df_1stpass.with_columns(
        (pl.col("capture_time").dt.hour() >= 16).cast(pl.Int8).alias("post_4pm")
    )
    # check to see if the 1stpass event occured after before 9:30 am, if yes create column pre_9_30 equal to 1
    df_1stpass = df_1stpass.with_columns(
        (
            (pl.col("capture_time").dt.hour() <= 9)
            & (pl.col("capture_time").dt.minute() < 30)
        )
        .cast(pl.Int8)
        .alias("pre_9_30")
    )

    df_1stpass = df_1stpass.with_columns(pl.col("derivedtickers").str.split("|"))
    df_1stpass = df_1stpass.explode("derivedtickers")
    df_1stpass = df_1stpass.with_columns(
        pl.col("capture_time").dt.strftime("%Y-%m-%d").alias("date")
    )


    df_1stpass = df_1stpass.group_by(["date", "derivedtickers"]).agg(
        [
            pl.col("post_4pm").sum().alias("n_news_post_close"),
            pl.col("pre_9_30").sum().alias("n_news_pre_open"),
        ]
    )

    # by story_id, keep the last row using polar's groupby and last
    # essentially, we are capturing the last update (in case some tickers are added later in event==UPDATES)
    df = df.group_by(["date", "story_id"]).last()

    # because of the UTC to EST, an article can show up in two different dates, we need to keep the one with the first entry.
    df = df.group_by("story_id").first()

    # keep the columns: story_id, derivedtickers, event, language_string, headline, body_text
    df = df.select(
        ["date", "time_of_arrival", "capture_time", "story_id", "derivedtickers", "derivedtickers_scores", "derivedtopics", "hot_level", "headline"]
    )
    # column derivedtickers is in this format "AAPL|MSFT|GOOGL", split it by "|" and explode it
    df = df.with_columns(pl.col("derivedtickers").str.split("|"))
    df = df.with_columns(pl.col("derivedtickers_scores").str.split("|").cast(pl.List(pl.Float64)))
    df = df.explode("derivedtickers")
    # drop duplicates using subset story_id and derivedtickers
    df = df.unique(subset=["story_id", "derivedtickers"])
    # keep tickers that shows up in the ticker list
    df = df.filter(pl.col("derivedtickers").is_in(ticker))

    # remove unwanted headlines that contains "QUOTATION RESUMED" and "TRADING RELEASED"
    df = df.filter(
        ~pl.col("headline").str.contains("QUOTATION RESUMED|TRADING RELEASED")
    )

    # save date, ticker, story_id, hot-level, headline
    head = df.select(["date", "derivedtickers", "story_id", "hot_level", "headline"])
    # keep unique rows
    head = head.unique(subset=["derivedtickers", "story_id"])
    df_headline.append(head)

    # create a dummy variable news_flash equal to 1 if the column "headline" starts with a "*"
    df = df.with_columns(
        (pl.col("headline").str.starts_with("*")).cast(pl.Int8).alias("news_flash")
    )

    # grouby by derivedtickers and sum the count of story_id
    df = df.group_by(["date", "derivedtickers"]).agg(
        pl.col("story_id").count().alias("blm_news_count"),
        pl.col("news_flash").sum().alias("blm_news_flash_count")
    )

    # merge df_1stpass with df on date and derivedtickers and keep the columns n_news_post_4 and n_news_pre_9_30
    df = df.join(df_1stpass, on=["date", "derivedtickers"], how="left")

    # fillna with 0 for n_news_post_close and n_news_pre_open
    df = df.with_columns(
        pl.col("n_news_post_close").fill_null(0), pl.col("n_news_pre_open").fill_null(0)
    )

    # rename columns derivedtickers to ticker
    df = df.rename({"derivedtickers": "ticker"})

    # append to df_blm
    df_blm.append(df)

# concatenate all the dataframes in df_blm
df_blm = pl.concat(df_blm)
# do another groupby by date and ticker to sum the blm_news_count in case dups in dates because of UTC to EST conversion
df_blm = df_blm.group_by(["date", "ticker"]).agg(
    [
        pl.col("blm_news_count").sum().alias("blm_news_count"),
        pl.col("blm_news_flash_count").sum().alias("blm_news_flash_count"),
        pl.col("n_news_post_close").sum().alias("n_news_post_close"),
        pl.col("n_news_pre_open").sum().alias("n_news_pre_open"),
    ]
)
# convert date that is in string format to datetime
df_blm = df_blm.with_columns(pl.col("date").str.strptime(pl.Date, format="%Y-%m-%d"))
# sort by date and ticker
df_blm = df_blm.sort(["date", "ticker"])
# save the dataframe to parquet
df_blm.write_parquet(output_dir / "bloomberg_daily_aggregation_crsp_ticker.parquet")

# save the headlines to parquet
df_headline = pl.concat(df_headline)
df_headline.write_parquet(
    output_dir / "bloomberg_daily_aggregation_headlines_crsp_ticker.parquet"
)

#%%
all_files_body = [f for f in os.listdir(input_directory) if "34151" in f]

# in all files, keep only files for which the date is after 2019
all_files_body = [
    f
    for f in all_files_body
    if int(re.search(r"_(\d{8})\.parquet$", f).group(1)) >= 20190101
]

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
    output_dir / "bloomberg_daily_aggregation_body_crsp_ticker_20190101_20240930.parquet"
)