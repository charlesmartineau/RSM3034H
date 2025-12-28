# This code is an example on how to extract news from the parquet files

#%%
import os
import re
from tqdm import tqdm
import polars as pl
import pandas as pd



# Set the directory containing the Parquet files
input_directory = "H:/data_common_master/Bloomberg_News/parquet/"
output_dir = "H:/users_fac/martineau_charles/bloomberg_news_aggregation/us/"

#%%
# List of topics to filter for
target_topics = {}
# target_topics = {
#    "SPLC",
#    "SPLCARD",
#    "SUPPLYDISR",
#    "SPLCWATCH",
#    "SPLCMOVUS",
#    "SUPPLY",
#    "SPLCPREV",
#   "TRADENL",
#    "PANAMA",
# }



all_files = os.listdir(input_directory)
# keep only files that contains the <body> content which are the files that start with EID34151
all_files = [f for f in all_files if f.startswith("EID34151")]

count = 1
impose_topics = False
keep_read = True

# Define the columns to keep
columns_to_keep = [
    "story_id",
    "capture_time",
    "time_of_arrival",
    "event",
    "headline",
    #"body",
    "derivedtickers",
    "derivedtopics",
    "derivedpeople",
    "language_string",
    "hot_level"
]

# Function to extract year from filename
def extract_year(filename):
    match = re.search(r'_(\d{4})\d{4}\.parquet$', filename)
    return match.group(1) if match else None

def retrieve_read_count(df_):
    if "derivedtopics" in df_.columns:
        # some columns derivedtopics are saved as object in the parquet file
        df_['derivedtopics'] = df_['derivedtopics'].astype(str)
        df_ = df_[
            df_["derivedtopics"].apply(
                lambda x: "READ" in x.split("|")
            )
        ]

    # loop over columns "derivedtopics" and create new column with the match = re.match(r'READ(\d+)', topic_text)
    df_["read_count"] = [
        max(
            re.findall(r"\bREAD\d*", i),
            key=lambda x: int(x[4:]) if x[4:].isdigit() else float("-inf"),
        )
        for i in df_["derivedtopics"]
    ]

    # remove rows for which 'READ' does not contain a number.
    df_ = df_[df_['read_count'] != 'READ']

    # remove duplicates for which story_id is the same and read is the same. keep first. this is because there are additional attribute updates
    df_ = df_.sort_values(
        by=["story_id", "capture_time"]
    )
    df_ = df_.drop_duplicates(
        subset=["story_id", "read_count"],
        keep="first",
    )
    return df_

# Split files into years
files_by_year = {}
for filename in all_files:
    year = int(extract_year(filename))
    if year:
        if year not in files_by_year:
            files_by_year[year] = []
        files_by_year[year].append(filename)

for year in range(2015, 2025):
    # Initialize an empty list to store filtered data
    filtered_data = []

    all_files = files_by_year[year]
    # Loop through all parquet files in the directory
    for filename in tqdm(all_files):
        print(f"Working on file {filename}")
        count += 1

        if filename.endswith(".parquet"):
            file_path = os.path.join(input_directory, filename)

            # Read the parquet file
            df = pl.read_parquet(file_path, columns=columns_to_keep)


            # Ensure 'derivedtopics' column exists
            #if impose_topics:
            #    if "derivedtopics" in df.columns:
            #        # Filter rows where at least one of the target topics is in the derivedtopics column
            #        df = df[
            #            df["derivedtopics"].apply(
            #                lambda x: any(topic in x.split("|") for topic in target_topics)
            #            )
            #        ]

            # keep english news
            df = df.filter(pl.col("language_string") == "ENGLISH")
            df = df.drop("language_string")

            # select first_pass (does not contain read count)
            df_first_pass = df.filter(pl.col("event") == "ADD_1STPASS").to_pandas()
            # select add_story (also include first pass)
            df_add_story = df.filter(pl.col("event") == "ADD_STORY").to_pandas()
            df_non_first_pass = df.filter(
                (pl.col("event") != "ADD_1STPASS") & (pl.col("event") != "ADD_STORY")
            ).to_pandas()

            # see if any of the add_story has a read count
            if keep_read and not df_add_story.empty:
                df_add_story_with_read = retrieve_read_count(df_add_story)

            # retrieve the read count from the updates
            if keep_read and not df_non_first_pass.empty:
                df_non_first_pass = retrieve_read_count(df_non_first_pass)

        if not df_add_story_with_read.empty:
            df_story = df_add_story.merge(df_add_story_with_read[['story_id', 'capture_time', 'read_count']],
                                          on=['story_id', 'capture_time'], how='left')

            df_ = pd.concat([df_first_pass, df_story, df_non_first_pass], ignore_index=True)

        else:
            df_ = pd.concat([df_first_pass, df_add_story, df_non_first_pass], ignore_index=True)

        df_ = df_.sort_values(by=["story_id", "capture_time"])

        filtered_data.append(df_)

    final_df = pd.concat(filtered_data, ignore_index=True)

    # keep only the first entry by story_id, event, and read_count
    # This makes sure that we have 1st_pass, add_story, and unique read_count for each updates
    final_df = final_df.drop_duplicates(
        subset=["story_id", "event", "read_count"],
        keep="first")

    final_df = final_df.sort_values(by=['story_id',  "event", 'capture_time'])

    # Save to a new parquet file
    final_df.to_parquet(f"{output_file}bloomberg_aggregated_{year}.parquet", index=False)
    print(f"Filtered articles saved to {output_file}")

