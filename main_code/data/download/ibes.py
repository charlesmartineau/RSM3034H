import pandas as pd
import wrds

start_date = "01/01/2000"
end_date = "12/31/2024"


def get_ibes_estimates(
    wrds_username: str,
    wrds_password: str,
    start_date: str = "01/01/2000",
    end_date: str = "12/31/2024",
) -> pd.DataFrame:
    """
    Retrieve IBES unadjusted estimates from WRDS. Estimates consists of analyst forecasts of quarterly EPS.
    "fpi in (6,7)" selects quarterly forecast for the current and the next fiscal quarter.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
        start_date (str): The beginning date for the estimates in the format 'MM-DD-YYYY'.
        end_date (str): The end date for the estimates in the format 'MM-DD-YYYY'.
    """
    import wrds

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    ibes_ana_est = conn.raw_sql(
        f"""
                        select ticker, estimator, analys, pdf, fpi, value, 
                        fpedats, revdats, revtims, anndats, anntims
                        from ibes.detu_epsus 
                        where fpedats between '{start_date}' and '{end_date}'
                        and (fpi='6' or fpi='7')
                        """,
        date_cols=["revdats", "anndats", "fpedats"],
    )

    conn.close()
    return ibes_ana_est


def get_ibes_actuals(
    wrds_username: str,
    wrds_password: str,
    start_date: str = "01/01/2000",
    end_date: str = "12/31/2024",
) -> pd.DataFrame:
    """
    Get IBES actuals from WRDS. Actuals consists of actual EPS reported by companies.

    Args:
        wrds_username (str): A WRDS username to use for the connection.
        wrds_password (str): A WRDS password to use for the connection.
        start_date (str): The start date for the actuals in the format 'MM-DD-YYYY'.
        end_date (str): The end date for the actuals in the format 'MM-DD-YYYY'.
    """

    conn = wrds.Connection(wrds_username=wrds_username, wrds_password=wrds_password)

    ibes_act = conn.raw_sql(
        f"""
                                select ticker, anndats as repdats, value as act, pends as fpedats, pdicity,
                                anntims as repdats_time
                                from ibes.actu_epsus 
                                where pends between '{start_date}' and '{end_date}'
                                and pdicity='QTR'
                                """,
        date_cols=["repdats", "fpedats"],
    )

    conn.close()
    return ibes_act
