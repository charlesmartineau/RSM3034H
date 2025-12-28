import os

import polars as pl


def retrieve_ravenpack_full_articles(news_type="equities"):
    """
    This function retrieves full articles from the Ravenpack database for US equities and global macro.
    It filters the data based on specific criteria and processes the headlines.
    The final DataFrame is saved to a parquet file. This code is not part of the main pipeline and is used for data retrieval only.
    """
    df_full = []

    files = os.listdir(f"H:/data_common_master/Ravenpack/djpr_{news_type}/")

    for file in files:
        print(file)
        df = pl.read_parquet(f"H:/data_common_master/Ravenpack/djpr_{news_type}/{file}")

        df = df.filter(
            (pl.col("news_type") == "FULL-ARTICLE")
            & (pl.col("rp_source_id") == "AA6E89")
            & (pl.col("country_code") == "US")
        )

        # convert utc to est time

        df = df.with_columns(
            pl.col("timestamp_utc")
            .dt.convert_time_zone("America/New_York")
            .alias("timestamp_est"),
        )

        # sort by timestamp_utc
        df = df.sort("timestamp_utc")

        # convert columns headline in lower case
        df = df.with_columns(
            pl.col("headline").str.to_lowercase().alias("headline"),
            pl.col("event_text").str.to_lowercase().alias("event_text"),
        )

        # create column "wsj_blog" == 1 if wsj blog is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("wsj blog"))
            .then(1)
            .otherwise(0)
            .alias("wsj_blog")
        )

        # create column "wsj_com" == 1 if wsj.com is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("wsj.com"))
            .then(1)
            .otherwise(0)
            .alias("wsj_com")
        )

        # create column "live_blog" == 1 if live blog is in headline, else 0
        df = df.with_columns(
            pl.when(
                pl.col("headline").str.contains("live blog")
                | pl.col("headline").str.contains("live:")
            )
            .then(1)
            .otherwise(0)
            .alias("live_blog")
        )

        # create a column "wsje" equal to 1 if wsje is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("wsje"))
            .then(1)
            .otherwise(0)
            .alias("wsje")
        )

        # create a column "awsj" equal to 1 if awsj is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("awsj"))
            .then(1)
            .otherwise(0)
            .alias("awsj")
        )
        # create a column "web_video" equal to 1 if "web video" is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("web video"))
            .then(1)
            .otherwise(0)
            .alias("web_video")
        )
        # create a column "barrons_blog" equal to 1 if "barron's blog" is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("barron's blog"))
            .then(1)
            .otherwise(0)
            .alias("barrons_blog")
        )

        # create column "update" equal to 1 if "-- update" is in headline, else 0
        df = df.with_columns(
            pl.when(
                pl.col("headline").str.contains("-- update")
                | pl.col("headline").str.contains("update:")
                | pl.col("headline").str.contains("2nd update")
                | pl.col("headline").str.contains("3rd update")
            )
            .then(1)
            .otherwise(0)
            .alias("update")
        )

        # create a column "all_things_digital" == 1 if "all things digital" is in headline, else 0
        df = df.with_columns(
            pl.when(
                pl.col("headline").str.contains("all things d:")
                | pl.col("headline").str.contains("all things digital")
                | pl.col("headline").str.contains("-- all things d")
            )
            .then(1)
            .otherwise(0)
            .alias("all_things_digital")
        )

        # create a column "test_message" equal to 1 if "test message" is in headline, else 0
        df = df.with_columns(
            pl.when(pl.col("headline").str.contains("test message:"))
            .then(1)
            .otherwise(0)
            .alias("test_message")
        )

        # groupby rp_entity_id and rp_story_id and take the first row
        df = df.group_by(["rp_entity_id", "rp_story_id"]).first()

        # reorder columns
        df = df.select(
            [
                "rp_story_id",
                "timestamp_est",
                "rp_entity_id",
                "entity_name",
                "event_text",
                "headline",
                "relevance",
                "event_relevance",
                "event_sentiment_score",
                "topic",
                "group",
                "type",
                "sub_type",
                "property",
                "fact_level",
                "category",
                "wsj_blog",
                "live_blog",
                "wsj_com",
                "wsje",
                "awsj",
                "barrons_blog",
                "web_video",
                "update",
                "all_things_digital",
                "test_message",
            ]
        )

        df = df.with_columns(pl.lit(news_type).alias("news_type"))

        df_full.append(df)

    df_full = pl.concat(df_full)

    # save the dataframe to a parquet file
    df_full.write_parquet(
        f"H:/users_fac/martineau_charles/data/restricted/ravenpack/rpa_djpr_{news_type}_full_articles.parquet"
    )

    return df_full


eq = retrieve_ravenpack_full_articles(news_type="equities")
macro = retrieve_ravenpack_full_articles(news_type="global_macro")
