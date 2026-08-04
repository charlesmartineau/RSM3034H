"""
Scheduled FOMC meeting dates from federalreserve.gov.

The Fed publishes its meeting calendar on two pages with different markup:

* historical pages, one per year, ``fomchistorical{YYYY}.htm``, through 2020
* the rolling calendar page, ``fomccalendars.htm``, from 2021 onwards

For the announcement premium we want the *announcement date*, which is the
**last** day of the meeting: the policy statement is released at ~2:00pm ET on
the second day of a two-day meeting.  Three rules are applied, in order:

1. a meeting spanning two days contributes only its last day
2. only regularly scheduled meetings count -- conference calls, meetings marked
   ``(unscheduled)`` and ``(notation vote)`` entries are excluded, because their
   timing is endogenous to market conditions
3. cancelled meetings are dropped -- the scheduled March 17-18, 2020 meeting
   never produced an announcement

The FOMC holds eight regularly scheduled meetings a year, which is the check
:func:`validate_fomc_meetings` runs against the parsed result.  The one
exception since 1994 is 2020, which has seven because of the cancelled March
meeting.
"""

import logging
import re
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import requests
from lxml import html as lhtml

HISTORICAL_URL = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

# The FOMC only began announcing its policy decision on the day of the meeting
# in February 1994; before that the decision had to be inferred from open-market
# operations over the following days, so there is no announcement day to date.
FIRST_ANNOUNCEMENT_YEAR = 1994

# Regularly scheduled meetings per calendar year, and the one exception.
MEETINGS_PER_YEAR = 8
MEETINGS_PER_YEAR_EXCEPTIONS = {2020: 7}  # March 17-18 meeting was cancelled

_HEADERS = {"User-Agent": "Mozilla/5.0 (RSM3034H research; academic use)"}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_MONTH = r"[A-Za-z]{3,9}"

# "April/May 30-1" -- two-day meeting spanning a month boundary
_RE_SLASH_MONTHS = re.compile(rf"^({_MONTH})\s*/\s*({_MONTH})\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})$")
# "January 31-February 1" -- the same thing written out in full
_RE_TWO_MONTHS = re.compile(rf"^({_MONTH})\s+(\d{{1,2}})\s*-\s*({_MONTH})\s+(\d{{1,2}})$")
# "January 28-29" -- two-day meeting inside one month
_RE_RANGE = re.compile(rf"^({_MONTH})\s+(\d{{1,2}})\s*-\s*(\d{{1,2}})$")
# "March 18" -- one-day meeting
_RE_SINGLE = re.compile(rf"^({_MONTH})\s+(\d{{1,2}})$")

# The historical pages carry the meeting type in the <h5> heading text.  On
# pre-2011 pages the tag is bare (``<h5>``); from 2011 it carries attributes,
# hence ``<h5[^>]*>``.
_RE_H5 = re.compile(r"<h5[^>]*>(.*?)</h5>", re.DOTALL | re.IGNORECASE)
_RE_TAG = re.compile(r"<[^>]+>")
_RE_YEAR_SUFFIX = re.compile(r"\s*-\s*(\d{4})\s*$")
_RE_QUALIFIER = re.compile(r"\((unscheduled|cancell?ed|notation vote)\)", re.IGNORECASE)
_RE_TRAILING_TYPE = re.compile(r"\s*(conference call|meeting)\s*$", re.IGNORECASE)

# On the calendar page a Summary of Economic Projections is flagged with a
# trailing asterisk on the date, e.g. "17-18*".
_RE_SEP_STAR = re.compile(r"\*+")


def _parse_month(name: str) -> Optional[int]:
    return _MONTHS.get(name.strip().lower().rstrip("."))


def _parse_date_range(text: str, year: int) -> Optional[tuple[date, date]]:
    """
    Parse the date portion of a meeting entry into (start_date, end_date).

    Handles the four layouts the Fed uses: "March 18", "January 28-29",
    "January 31-February 1" and "April/May 30-1".  Returns None if the text
    does not look like a meeting date.
    """
    text = " ".join(text.split())

    if m := _RE_SLASH_MONTHS.match(text):
        month1, month2, day1, day2 = _parse_month(m[1]), _parse_month(m[2]), int(m[3]), int(m[4])
    elif m := _RE_TWO_MONTHS.match(text):
        month1, day1, month2, day2 = _parse_month(m[1]), int(m[2]), _parse_month(m[3]), int(m[4])
    elif m := _RE_RANGE.match(text):
        month1 = month2 = _parse_month(m[1])
        day1, day2 = int(m[2]), int(m[3])
    elif m := _RE_SINGLE.match(text):
        month1 = month2 = _parse_month(m[1])
        day1 = day2 = int(m[2])
    else:
        return None

    if month1 is None or month2 is None:
        return None

    # A meeting running from December into January rolls the year over.
    end_year = year + 1 if month2 < month1 else year
    try:
        return date(year, month1, day1), date(end_year, month2, day2)
    except ValueError:
        return None


def _parse_historical_heading(heading: str) -> Optional[dict]:
    """
    Parse one <h5> heading from a historical FOMC page.

    Headings look like ``January 29-30 Meeting - 2008``,
    ``March 10 Conference Call - 2008``, ``March 17-18 (cancelled) Meeting -
    2020`` or ``August 27 (notation vote) - 2020``: the meeting type is fully
    recoverable from the heading text.
    """
    text = " ".join(_RE_TAG.sub(" ", heading).split())

    year_match = _RE_YEAR_SUFFIX.search(text)
    if not year_match:
        return None
    year = int(year_match[1])
    text = text[: year_match.start()]

    qualifier = _RE_QUALIFIER.search(text)
    qualifier = qualifier[1].lower() if qualifier else None
    text = _RE_QUALIFIER.sub(" ", text)

    trailing = _RE_TRAILING_TYPE.search(text)
    base_type = trailing[1].lower() if trailing else "meeting"
    text = _RE_TRAILING_TYPE.sub("", text)

    dates = _parse_date_range(text, year)
    if dates is None:
        logging.debug(f"Could not parse FOMC heading: {heading!r}")
        return None
    start_date, end_date = dates

    if qualifier == "notation vote":
        meeting_type = "notation vote"
    elif qualifier in ("cancelled", "canceled"):
        meeting_type = "cancelled meeting"
    elif qualifier == "unscheduled":
        meeting_type = "unscheduled meeting"
    elif base_type == "conference call":
        meeting_type = "conference call"
    else:
        meeting_type = "meeting"

    return {
        "start_date": start_date,
        "end_date": end_date,
        "meeting_type": meeting_type,
        "scheduled": meeting_type == "meeting",
    }


def _fetch(url: str, timeout: int = 30) -> str:
    response = requests.get(url, headers=_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def _parse_historical_year(year: int) -> list[dict]:
    """Parse all meeting entries from one historical FOMC page."""
    html = _fetch(HISTORICAL_URL.format(year=year))
    meetings = [
        parsed
        for heading in _RE_H5.findall(html)
        if (parsed := _parse_historical_heading(heading)) is not None
    ]
    return _merge_consecutive_meetings(meetings)


def _merge_consecutive_meetings(meetings: list[dict]) -> list[dict]:
    """
    Merge scheduled meetings listed as consecutive single days into one meeting.

    The 2003 page lists the two-day September meeting as two separate headings,
    ``September 15 Meeting`` and ``September 16 Meeting``.  Left alone that
    yields nine scheduled dates for 2003 instead of eight, so the entries have
    to be merged before the last-day rule is applied.
    """
    meetings = sorted(meetings, key=lambda m: (m["start_date"], m["end_date"]))

    merged: list[dict] = []
    for meeting in meetings:
        previous = merged[-1] if merged else None
        if (
            previous is not None
            and previous["scheduled"]
            and meeting["scheduled"]
            and meeting["start_date"] == previous["end_date"] + timedelta(days=1)
        ):
            previous["end_date"] = meeting["end_date"]
        else:
            merged.append(dict(meeting))
    return merged


def _parse_calendar_page() -> list[dict]:
    """
    Parse the rolling calendar page, which covers 2021 onwards.

    The markup differs from the historical pages: each year sits in a panel
    headed ``<h4>YYYY FOMC Meetings</h4>`` holding ``fomc-meeting__month`` /
    ``fomc-meeting__date`` divs with values like ``January`` / ``27-28``.
    ``(notation vote)`` rows are dropped and the trailing ``*`` marking a
    Summary of Economic Projections is stripped.
    """
    tree = lhtml.fromstring(_fetch(CALENDAR_URL))

    meetings: list[dict] = []
    seen_years: set[int] = set()
    for panel in tree.xpath('//div[contains(@class, "panel")]'):
        heading = " ".join(x.strip() for x in panel.xpath(".//h4//text()")).strip()
        year_match = re.match(r"^(\d{4})\s+FOMC Meetings", heading)
        if not year_match:
            continue
        year = int(year_match[1])
        if year in seen_years:
            continue

        rows = panel.xpath(
            './/div[contains(@class, "fomc-meeting")][contains(@class, "row")]'
        )
        year_meetings: list[dict] = []
        for row in rows:
            month = " ".join(
                x.strip()
                for x in row.xpath('.//div[contains(@class, "fomc-meeting__month")]//text()')
            ).strip()
            day = " ".join(
                x.strip()
                for x in row.xpath('.//div[contains(@class, "fomc-meeting__date")]//text()')
            ).strip()
            if not month or not day:
                continue

            qualifier = _RE_QUALIFIER.search(day)
            qualifier = qualifier[1].lower() if qualifier else None
            day = _RE_SEP_STAR.sub("", _RE_QUALIFIER.sub("", day)).strip()

            dates = _parse_date_range(f"{month} {day}", year)
            if dates is None:
                logging.debug(f"Could not parse FOMC calendar row: {month!r} {day!r}")
                continue
            start_date, end_date = dates

            if qualifier == "notation vote":
                meeting_type = "notation vote"
            elif qualifier in ("cancelled", "canceled"):
                meeting_type = "cancelled meeting"
            elif qualifier == "unscheduled":
                meeting_type = "unscheduled meeting"
            else:
                meeting_type = "meeting"

            year_meetings.append(
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "meeting_type": meeting_type,
                    "scheduled": meeting_type == "meeting",
                }
            )

        if year_meetings:
            seen_years.add(year)
            meetings.extend(_merge_consecutive_meetings(year_meetings))

    return meetings


def validate_fomc_meetings(meetings: pd.DataFrame) -> list[str]:
    """
    Check the parsed calendar against what the FOMC actually does.

    The scraper depends on the layout of two Fed pages, so it must be checked
    rather than trusted: a silently changed page should show up in the run log,
    not in the regression.  Returns a list of human-readable problems, empty if
    the calendar looks right.
    """
    problems: list[str] = []

    scheduled = meetings[meetings["scheduled"]]
    if scheduled.empty:
        return ["no scheduled FOMC meetings were parsed"]

    dates = scheduled["date"]
    if not dates.is_monotonic_increasing:
        problems.append("announcement dates are not sorted")
    if dates.duplicated().any():
        duplicates = sorted(dates[dates.duplicated()].dt.date.unique())
        problems.append(f"duplicate announcement dates: {duplicates}")
    if len(weekend := dates[dates.dt.dayofweek >= 5]) > 0:
        problems.append(f"announcement dates on a weekend: {sorted(weekend.dt.date)}")

    counts = dates.dt.year.value_counts()
    # The final year on the Fed's calendar page is complete, but do not require
    # anything of years the pages do not cover.
    for year in range(FIRST_ANNOUNCEMENT_YEAR, int(dates.dt.year.max()) + 1):
        expected = MEETINGS_PER_YEAR_EXCEPTIONS.get(year, MEETINGS_PER_YEAR)
        actual = int(counts.get(year, 0))
        if actual != expected:
            problems.append(
                f"{year}: parsed {actual} scheduled announcement dates, expected {expected}"
            )

    return problems


def get_fomc_meetings(
    start_year: int = FIRST_ANNOUNCEMENT_YEAR,
    end_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Scrape FOMC meeting dates from federalreserve.gov.

    Args:
        start_year (int): First calendar year to scrape. Defaults to 1994, the
            first year in which the FOMC announced its decision on the day of
            the meeting.
        end_year (int, optional): Last calendar year to scrape. Defaults to the
            last year on the Fed's calendar page.

    Returns:
        pd.DataFrame: One row per meeting, with columns

            * ``date``: the announcement date, i.e. the **last** day of the
              meeting -- this is the date the FOMC dummy is built on
            * ``start_date``, ``end_date``: the first and last day of the meeting
            * ``meeting_type``: ``meeting``, ``conference call``,
              ``notation vote``, ``unscheduled meeting`` or ``cancelled meeting``
            * ``scheduled``: True only for regularly scheduled meetings

        Unscheduled entries are kept rather than dropped so that the exclusions
        are visible in the saved file, but only rows with ``scheduled == True``
        belong in the announcement dummy.
    """
    calendar_meetings = _parse_calendar_page()
    if not calendar_meetings:
        raise ValueError(f"No FOMC meetings parsed from {CALENDAR_URL}")
    first_calendar_year = min(m["start_date"].year for m in calendar_meetings)

    meetings = list(calendar_meetings)
    for year in range(start_year, first_calendar_year):
        meetings.extend(_parse_historical_year(year))

    df = pd.DataFrame(meetings)
    # The announcement lands at ~2:00pm ET on the last day of the meeting.
    df["date"] = pd.to_datetime(df["end_date"])
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    df = df[df["date"].dt.year >= start_year]
    if end_year is not None:
        df = df[df["date"].dt.year <= end_year]

    df = df[["date", "start_date", "end_date", "meeting_type", "scheduled"]]
    df = df.sort_values("date").reset_index(drop=True)

    n_scheduled = int(df["scheduled"].sum())
    logging.info(
        f"Parsed {len(df)} FOMC meeting entries, {n_scheduled} regularly scheduled, "
        f"{df['date'].min():%Y-%m-%d} to {df['date'].max():%Y-%m-%d}"
    )
    for problem in validate_fomc_meetings(df):
        logging.warning(f"FOMC calendar check: {problem}")

    return df
