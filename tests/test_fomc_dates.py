"""
Validation tests for the scraped FOMC announcement calendar.

The scraper depends on the layout of two pages on federalreserve.gov, so it has
to be checked rather than trusted.  The check that does the work is the meeting
count: the FOMC holds eight regularly scheduled meetings per calendar year, and
that has held every year since 1994 with exactly one exception -- 2020, which
has seven, because the scheduled March 17-18 meeting was cancelled and the Fed
acted at the unscheduled March 15 meeting instead.

The tests read ``fomc_meetings.parquet`` out of the download cache, so run

    uv run main.py data.download=true

at least once first.  They are skipped if the file is not there.
"""

import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

from main_code.data.download.fomc import (
    FIRST_ANNOUNCEMENT_YEAR,
    MEETINGS_PER_YEAR,
    MEETINGS_PER_YEAR_EXCEPTIONS,
)
from main_code.utils.files import get_latest_file

load_dotenv()


@pytest.fixture(scope="module")
def meetings() -> pd.DataFrame:
    """The full parsed FOMC calendar, unscheduled entries included."""
    datadir = os.getenv("DATADIR")
    if not datadir:
        pytest.skip("DATADIR environment variable not set")

    file = get_latest_file(Path(datadir) / "download_cache" / "fomc_meetings.parquet")
    if file is None:
        pytest.skip(
            "fomc_meetings.parquet not in the download cache; "
            "run `uv run main.py data.download=true` first"
        )

    return pd.read_parquet(file)


@pytest.fixture(scope="module")
def announcements(meetings: pd.DataFrame) -> pd.DataFrame:
    """Regularly scheduled meetings only -- the ones the FOMC dummy is built on."""
    return meetings[meetings["scheduled"]].reset_index(drop=True)


def test_eight_scheduled_meetings_per_year_except_2020(announcements: pd.DataFrame):
    """Eight scheduled announcement dates every year, except 2020, which has seven."""
    counts = announcements["date"].dt.year.value_counts()
    last_year = int(announcements["date"].dt.year.max())

    for year in range(FIRST_ANNOUNCEMENT_YEAR, last_year + 1):
        expected = MEETINGS_PER_YEAR_EXCEPTIONS.get(year, MEETINGS_PER_YEAR)
        assert int(counts.get(year, 0)) == expected, (
            f"{year}: expected {expected} scheduled announcement dates, "
            f"got {int(counts.get(year, 0))}"
        )


def test_2020_has_seven_meetings(announcements: pd.DataFrame):
    """
    2020 is the exception, and its kept meetings are known.

    The cancelled March 17-18 meeting and the unscheduled March 2 / March 15
    meetings must all be excluded, as must the four notation votes.
    """
    dates_2020 = announcements.loc[
        announcements["date"].dt.year == 2020, "date"
    ].dt.strftime("%Y-%m-%d")

    assert list(dates_2020) == [
        "2020-01-29",
        "2020-04-29",
        "2020-06-10",
        "2020-07-29",
        "2020-09-16",
        "2020-11-05",
        "2020-12-16",
    ]


def test_one_announcement_date_per_meeting(announcements: pd.DataFrame):
    """
    Each meeting contributes exactly one date: the last day.

    A two-day meeting listed as ``January 28-29`` sets the dummy on the 29th
    only -- the statement is released at ~2:00pm ET on the second day.
    """
    assert (announcements["date"] == announcements["end_date"]).all()
    assert (announcements["start_date"] <= announcements["end_date"]).all()
    # No meeting runs longer than two days.
    lengths = (announcements["end_date"] - announcements["start_date"]).dt.days
    assert lengths.between(0, 1).all()


def test_announcement_dates_are_unique_and_sorted(announcements: pd.DataFrame):
    assert not announcements["date"].duplicated().any()
    assert announcements["date"].is_monotonic_increasing


def test_no_announcement_date_on_a_weekend(announcements: pd.DataFrame):
    weekend = announcements.loc[announcements["date"].dt.dayofweek >= 5, "date"]
    assert weekend.empty, f"announcement dates on a weekend: {list(weekend)}"


def test_sample_starts_in_1994(announcements: pd.DataFrame):
    """
    The FOMC only began announcing on the day of the meeting in February 1994.

    Before that the decision was inferred from open-market operations over the
    following days, so there is no announcement day to put a dummy on.
    """
    assert announcements["date"].min() == pd.Timestamp("1994-02-04")


def test_unscheduled_entries_are_parsed_but_flagged(meetings: pd.DataFrame):
    """
    Conference calls, unscheduled meetings and notation votes are kept in the
    file so the exclusions are visible, but never marked scheduled.
    """
    excluded = meetings[~meetings["scheduled"]]
    assert set(excluded["meeting_type"]) <= {
        "conference call",
        "unscheduled meeting",
        "cancelled meeting",
        "notation vote",
    }
    # The intermeeting cuts of 2008 and March 2020 must not be in the dummy.
    for endogenous_date in ["2008-01-22", "2008-10-08", "2020-03-03", "2020-03-15"]:
        assert not meetings.loc[
            meetings["date"] == endogenous_date, "scheduled"
        ].any(), f"{endogenous_date} should not be a scheduled announcement date"
