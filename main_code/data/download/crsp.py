import numpy as np
import pandas as pd
import wrds


def get_crsp_daily(
    wrds_username: str,
    wrds_password: str,
    CRSP_START_DATE="20070101",
    CRSP_END_DATE="20241231",
) -> pd.DataFrame:
    """
    Download CRSP daily stock file data and return a DataFrame.
    By the default, stocks with SHRCD between 10 and 11 and EXCHCD between 1 and 3 are selected.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
        CRSP_START_DATE (str): The start date to download data for.
        CRSP_END_DATE (str): The end date to download data for.
    """
    import wrds

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    query = f"""
    select a.date, a.permno, a.shrout, a.cfacpr, a.cfacshr, a.openprc, 
    b.ticker, b.comnam, b.exchcd, b.shrcd, b.ncusip, a.PRC, a.VOL, a.RET
    from crsp.dsf as a
    left join crsp.dsenames as b
    on a.PERMNO=b.PERMNO
    and b.namedt<=a.date
    and a.date<=b.nameendt
    where b.SHRCD between 10 and  11
    and b.EXCHCD between 1 and  3
    and (a.date >= '{CRSP_START_DATE}') and (a.date <= '{CRSP_END_DATE}')"""

    df = conn.raw_sql(query)

    # clean data
    df["date"] = pd.to_datetime(df["date"])
    df["prc"] = np.abs(df["prc"])
    df["permno"] = df["permno"].astype(int)

    conn.close()
    return df


def get_crsp_monthly(
    wrds_username: str,
    wrds_password: str,
    CRSP_START_DATE="20070101",
    CRSP_END_DATE="20241231",
) -> pd.DataFrame:
    """
    Download CRSP monthly stock file data and return a DataFrame.
    By the default, stocks with SHRCD between 10 and 11 and EXCHCD between 1 and 3 are selected.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
        CRSP_START_DATE (str): The start date for the data.
        CRSP_END_DATE (str): The end date for the data.
    """

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    query = f"""
    select a.date, a.permno, a.shrout, a.cfacpr, a.cfacshr, 
    b.ticker, b.comnam, b.exchcd, b.shrcd, b.ncusip, a.prc, a.vol, a.ret, a.retx
    from crsp.msf as a
    left join crsp.dsenames as b
    on a.PERMNO=b.PERMNO
    and b.namedt<=a.date
    and a.date<=b.nameendt
    where b.SHRCD between 10 and  11
    and b.EXCHCD between 1 and  3
    and a.date >= '{CRSP_START_DATE}' and a.date <= '{CRSP_END_DATE}'  """

    df = conn.raw_sql(query)
    df["date"] = pd.to_datetime(df["date"])
    # push date to the end of the month
    df["date"] = df["date"] + pd.offsets.MonthEnd(0)
    df["prc"] = np.abs(df["prc"])
    df["permno"] = df["permno"].astype(int)

    conn.close()
    return df


def get_crsp_compu_link_table(
    wrds_username: str, wrds_password: str
) -> pd.DataFrame:
    """
    Download CRSP-Compustat link table and return a DataFrame.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
    """
    import wrds

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    query = """
    SELECT *
    FROM crsp.ccmxpf_linktable
    WHERE usedflag = 1
    AND linkprim IN ('P', 'C')
    """

    # Execute the query
    data = conn.raw_sql(query)
    data["linkdt"] = pd.to_datetime(data["linkdt"])
    data["linkenddt"] = pd.to_datetime(data["linkenddt"])

    conn.close()
    return data


def get_crsp_cfacshr(
    wrds_username: str,
    wrds_password: str,
    CRSP_START_DATE="01/01/1999",
    CRSP_END_DATE="12/31/2024",
) -> pd.DataFrame:
    """
    Retrieve CRSP adjustment factors for shares outstanding.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
        CRSP_START_DATE (str): The start date for the data.
        CRSP_END_DATE (str): The end date for the data.
    """
    import wrds

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    cfacshr = conn.raw_sql(
        f"""
                            select permno, date, cfacshr
                            from crsp.dsf
                            where date between '{CRSP_START_DATE}' and '{CRSP_END_DATE}'
                            """,
        date_cols=["date"],
    )

    conn.close()
    return cfacshr


def get_crsp_dates(wrds_username: str, wrds_password: str) -> pd.DataFrame:
    """
    Retrieve all trading dates from CRSP.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
    """
    import wrds

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    crsp_dates = conn.raw_sql(
        """ 
                                select date 
                                from crsp.dsi 
                            """,
        date_cols=["date"],
    )

    conn.close()
    return crsp_dates