# %%
import os
from pathlib import Path

import wrds
from dotenv import load_dotenv

#from ...utils import timestamp_file

# %%
load_dotenv()

# Get directories and credentials from environment (passed from main.py)
data_dir = Path(os.getenv("DATADIR"))
WRDS_USERNAME = os.getenv("WRDS_USERNAME")
WRDS_PASSWORD = os.getenv("WRDS_PASSWORD")


# Connect to WRDS
conn = wrds.Connection(wrds_username=WRDS_USERNAME, wrds_password=WRDS_PASSWORD)


def download_ravenpack_common_tables(conn: wrds.Connection):
    """
    Download all RavenPack common tables from the WRDS database.
    """

    # List all available tables in RavenPack DJDNA library
    tables = conn.list_tables(library="ravenpack_common")

    for table in (
        tables
    ):  # skip the first two tables which are not relevant (chars and common_chars)
        print(f"Downloading table: {table}")
        file_path = restricted_dir / "ravenpack" / f"{table}.parquet"

        conn.get_table(library="ravenpack_common", table=table).to_parquet(
            #file_path=timestamp_file(file_path), index=False
            file_path, index=False
        )
    # close connection
    conn.close()

def download_ravenpack_djpr_equity_tables(conn: wrds.Connection):
    """
    Download all RavenPack DJPR tables from the WRDS database.
    """

    for year in range(
        2000, 2025
    ):  # skip the first two tables which are not relevant (chars and common_chars)
        print(f"Downloading djpr table: {year}")
        file_path = restricted_dir / "ravenpack" / f"rpa_djpr_equities_{year}.parquet"
        conn.get_table(
            library="ravenpack_dj", table=f"rpa_djpr_equities_{year}"
        ).to_parquet(
            #timestamp_file(file_path), index=False,
            file_path, index=False

        )
    # close connection
    conn.close()

def download_ravenpack_djpr_global_tables(conn: wrds.Connection):
    """
    Download all RavenPack DJPR tables from the WRDS database.
    """

    for year in range(
        2000, 2025
    ):  # skip the first two tables which are not relevant (chars and common_chars)
        print(f"Downloading djpr table: {year}")
        #file_path = data_dir / "ravenpack" / f"rpa_djpr_global_macro_{year}.parquet"
        file_path = f"H:/data_common_master/Ravenpack/djpr_global_macro/rpa_djpr_global_macro_{year}.parquet"
        conn.get_table(
            library="ravenpack_dj", table=f"rpa_djpr_global_macro_{year}"
        ).to_parquet(
            #timestamp_file(file_path),
            file_path,
            index=False,
        )

    # close connection
    conn.close()


if __name__ == "__main__":
    #download_ravenpack_common_tables(conn)
    #download_ravenpack_djpr_equity_tables(conn)
    download_ravenpack_djpr_global_tables(conn)
