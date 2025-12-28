# in this code, loop over the retrieved headlines from the daily aggregation file and save the headlines and story.
#%%
import os
import re
from tqdm import tqdm
from pathlib import Path
import polars as pl
#%%

input_directory = Path("H:/data_common_master/Bloomberg_News/parquet/")
output_dir = Path("H:/users_fac/martineau_charles/data/restricted/bloomberg_news_aggregation/hk/")

# load crsp file
headlines = pl.read_parquet(output_dir / "bloomberg_daily_aggregation_headlines_hk_ticker.parquet")
story_id = headlines.select("story_id").unique().to_series().to_list()

all_files = [f for f in os.listdir(input_directory) if "34151" in f]

# split the all_files into years
def extract_year(filename):
    match = re.search(r'_(\d{4})\d{4}\.parquet$', filename)
    return match.group(1) if match else None

# Split files into years
files_by_year = {}
for filename in all_files:
    year = int(extract_year(filename))
    if year:
        if year not in files_by_year:
            files_by_year[year] = []
        files_by_year[year].append(filename)

# %%
for year in files_by_year:
    if year > 2015:
        continue
    print(f"Processing year: {year}")
    df_news = []

    for file in tqdm(files_by_year[year], desc="Processing Bloomberg News files", unit="file"):
        
        df = (
            pl.read_parquet(input_directory / file)
            .filter(
                (pl.col("story_id").is_in(story_id))
            )
            #.with_columns(
            #    pl.col("capture_time").dt.convert_time_zone("America/New_York")
            #)
        ).select(["capture_time", "time_of_arrival", "event", "story_id", "language_string", "derivedtickers", "derivedtopics", "headline", "body"])

        df = df.with_columns(
            pl.col("capture_time").dt.replace_time_zone(None)
        )
        df = df.with_columns(
            pl.col("time_of_arrival").dt.replace_time_zone(None)
        )

        # append to the list
        df_news.append(df)

    # concatenate all the dataframes in df_news
    df_news = pl.concat(df_news)
    # save the dataframe to a parquet file
    df_news.write_parquet(output_dir / f"bloomberg_story_hk_ticker_{year}.parquet")

