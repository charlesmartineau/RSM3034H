#%%
import os
from tqdm import tqdm
from pathlib import Path
import polars as pl

input_dir = Path("H:/data_common_master/Ravenpack/djpr_equities/")
output_dir = Path("H:/users_fac/martineau_charles/data/restricted/ravenpack/")

files = os.listdir(input_dir)

ravenpack_news = []
#%%
for file in tqdm(files, desc="Processing ravenpack yearly files"):
    print(file)
    df = (pl.read_parquet(input_dir / file).filter(pl.col("relevance") >=90).filter(pl.col("country_code") == "US"))
    df = df.group_by(["rp_story_id", "rp_entity_id"]).first()
    df = df.with_columns(
        pl.col("timestamp_utc").dt.convert_time_zone("America/New_York").alias("datetime_est"),
    )
    # create date column
    df = df.with_columns(pl.col("datetime_est").dt.strftime("%Y-%m-%d").alias("date"))

    # Create a dummy variable rp_story_full_article equal to 1 if news_type == "FULL-ARTICLE"
    df = df.with_columns(
        (pl.col("news_type") == "FULL-ARTICLE").cast(pl.Int8).alias("rp_story_full_article")
    )
    # Create a dummy variable rp_story_tabular equal to 1 if news_type == "TABULAR-MATERIAL"
    df = df.with_columns(
        (pl.col("news_type") == "TABULAR-MATERIAL").cast(pl.Int8).alias("rp_story_tabular")
    )
    # Create a dummy variable rp_story_news_flash equal to 1 if news_type == "NEWS-FLASH" OR "HOT-NEWS-FLASH"
    df = df.with_columns(
        ((pl.col("news_type") == "NEWS-FLASH") | (pl.col("news_type") == "HOT-NEWS-FLASH")).cast(pl.Int8).alias("rp_story_news_flash")
    )
    # Create a dummy variable rp_story_press_release equal to 1 if news_type == "PRESS-RELEASE"
    df = df.with_columns(
        (pl.col("news_type") == "PRESS-RELEASE").cast(pl.Int8).alias("rp_story_press_release")
    )
    # Create a dummy variable rp_story_sec equal to 1 if news_type string contains "SEC"
    df = df.with_columns(
        (pl.col("news_type").str.contains("SEC")).cast(pl.Int8).alias("rp_story_sec")
    )

    # find the most common entry in the "group" column per rp_story_id and rp_entity_id
    news = df.group_by(["date", "rp_entity_id"]).agg(
        pl.col("group").mode().alias("most_frequent_newstype")
    )
    # Create dummy if the news is after 16
    df = df.with_columns(
        (pl.col("datetime_est").dt.hour() >= 16).cast(pl.Int8).alias("post_4pm")
    )

    # Create dummy if the news is before 9:30 am
    df = df.with_columns(
        ((pl.col("datetime_est").dt.hour() <= 9) &
         (pl.col("datetime_est").dt.minute() < 30)).cast(pl.Int8).alias("pre_9_30")
    )

    df = df.select(['date', 'rp_story_id', 'rp_entity_id', 'rp_story_full_article',
                    'rp_story_tabular', 'rp_story_news_flash', 'rp_story_press_release', 'rp_story_sec',
                    'event_sentiment_score', 'post_4pm', 'pre_9_30'])
    # count the number of stories per date and rp_entity_id and compute the average event_sentiment_score
    df = df.group_by(["date", "rp_entity_id"]).agg(
        pl.col("rp_story_id").count().alias("rp_story_count"),
        pl.col("rp_story_full_article").sum().alias("rp_story_count_full_article"),
        pl.col("rp_story_tabular").sum().alias("rp_story_count_tabular"),
        pl.col("rp_story_news_flash").sum().alias("rp_story_count_news_flash"),
        pl.col("rp_story_press_release").sum().alias("rp_story_count_press_release"),
        pl.col("rp_story_sec").sum().alias("rp_story_count_sec"),
        pl.col("post_4pm").sum().alias("rp_story_count_post_close"),
        pl.col("pre_9_30").sum().alias("rp_story_count_pre_open"),
        pl.col("event_sentiment_score").mean().alias("average_rp_sent")
    )
    # merge with news
    df = df.join(news, on=["date", "rp_entity_id"], how="left")
    ravenpack_news.append(df)

ravenpack_news = pl.concat(ravenpack_news)
ravenpack_news.write_parquet(output_dir / "ravenpack_us_news_aggregated.parquet")