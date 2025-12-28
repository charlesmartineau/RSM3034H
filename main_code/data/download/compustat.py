import wrds


def get_compustat_quarterly(
    wrds_username: str,
    wrds_password: str,
    START_DATE: str = "01/01/1999",
    END_DATE: str = "12/31/2024",
):
    """
    Retrieve quarterly data from Compustat.s
    """

    # retrieve data
    query = f"""
                                select gvkey, fyearq, fqtr, conm, datadate, rdq, epsfxq, epspxq, cshoq, prccq, 
                                ajexq, spiq, cshprq, cshfdq, saleq, atq, fyr, ffoq, fdateq, datafqtr, cshoq*prccq as mcap  
                                from comp.fundq 
                                where consol='C' and popsrc='D' and indfmt='INDL' and datafmt='STD'
                                and datadate between '{START_DATE}' and '{END_DATE}' 
                                """

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)
    fundq = conn.raw_sql(query, date_cols=["datadate", "datafqtr", "rdq"])
    conn.close()
    return fundq


def get_compustat_gic_codes(wrds_username: str, wrds_password: str):
    query = """
            select gvkey, gsector, ggroup, gind, gsubind, indfrom, indthru
            from comp.co_hgic 
            """

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)
    gic = conn.raw_sql(query, date_cols=["indfrom", "indthru"])
    conn.close()
    return gic
