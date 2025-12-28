import os
from tqdm import tqdm
from pathlib import Path
import polars as pl

input_dir = Path("H:/data_common_master/Ravenpack/djpr_equities/")
output_dir = Path("H:/users_fac/martineau_charles/data/restricted/ravenpack/")

files = os.listdir(input_dir)

earnings_news = []


for file in tqdm(files, desc="Processing ravenpack yearly files"):
    print(file)
    df = pl.read_parquet(input_dir / file)
    df = df.filter(pl.col("headline").str.contains("Calendar of U.S. Earnings Expected in the Week Ahead", literal=False))
    df = df.select(["timestamp_utc", "rp_story_id", "rp_entity_id", "entity_name", "headline"])
    df = df.with_columns(
        pl.col("timestamp_utc").dt.convert_time_zone("America/New_York").alias("timestamp_est"),
    )

    earnings_news.append(df)


earnings_news = pl.concat(earnings_news)

earnings_news.write_parquet(output_dir / "ravenpack_calendar_week_ahead_earnings_news.parquet")

