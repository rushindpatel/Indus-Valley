"""Tests for the IM77 frequency-table parser.

The first group uses a small made-up report, so it always runs. The second
group checks the real exports from indusscript.in and runs only when they have
been placed in data/raw/im77_rmrl/ (see data/README.md).
"""
from pathlib import Path

import pytest

from indus.im77_ngrams import (
    check_consistency,
    column_names,
    load_csv,
    parse_report,
    parse_report_file,
    write_csv,
)

# A made-up report in the layout of the real ones: a four-line header, CRLF
# line endings, and a three-line header repeated at a page break.
SAMPLE_DOUBLETS = (
    "IM77RMRL\r\n"
    "IM77 Frequency Tables\r\n"
    "Doublets frequencies greater than 0\r\n"
    "3records found\r\n"
    "2 1\r\n"
    "7\r\n"
    "3 2\r\n"
    "4\r\n"
    "\r\n"
    "IM77RMRL\r\n"
    "IM77 Frequency Tables\r\n"
    "Doublets frequencies greater than 0\r\n"
    "5 4\r\n"
    "1\r\n"
)


def test_parses_rows_and_skips_repeated_headers():
    report = parse_report(SAMPLE_DOUBLETS.splitlines(keepends=True), 2)
    assert report.declared_records == 3
    assert report.rows == [((2, 1), 7), ((3, 2), 4), ((5, 4), 1)]
    assert report.ok


def test_wrong_record_total_is_not_ok():
    text = SAMPLE_DOUBLETS.replace("3records found", "4records found")
    report = parse_report(text.splitlines(keepends=True), 2)
    assert len(report.rows) == 3
    assert not report.ok


def test_unexpected_line_is_reported_not_skipped():
    text = SAMPLE_DOUBLETS.replace("3 2\r\n", "3 2 9\r\n")
    report = parse_report(text.splitlines(keepends=True), 2)
    assert report.problems
    assert not report.ok


def test_sign_row_without_count_is_reported():
    report = parse_report((SAMPLE_DOUBLETS + "8 9\r\n").splitlines(keepends=True), 2)
    assert report.problems[-1][1] == "sign row without a count"


def test_duplicate_row_is_not_ok():
    text = SAMPLE_DOUBLETS.replace("5 4\r\n", "2 1\r\n")
    report = parse_report(text.splitlines(keepends=True), 2)
    assert report.duplicates == [(2, 1)]
    assert not report.ok


def test_csv_round_trip_and_reading_order(tmp_path):
    report = parse_report(SAMPLE_DOUBLETS.splitlines(keepends=True), 2)
    out = tmp_path / "pairs.csv"
    write_csv(report, str(out))
    assert out.read_text().splitlines()[0] == "left_sign,right_sign,count"
    assert load_csv(str(out)) == {(2, 1): 7, (3, 2): 4, (5, 4): 1}
    # Read right to left: the right-hand sign comes first.
    assert load_csv(str(out), reading_order=True) == {(1, 2): 7, (2, 3): 4, (4, 5): 1}


def test_column_names():
    assert column_names(3) == ("left_sign", "middle_sign", "right_sign")


def test_consistency_passes_when_tables_agree():
    doublets = {(3, 2): 4, (2, 1): 7}
    triplets = {(3, 2, 1): 4}
    result = check_consistency(doublets, triplets)
    assert result.implied_pairs == 2
    assert not result.missing and not result.undercounted
    assert result.shortfall == 0


def test_consistency_finds_missing_and_undercounted_pairs():
    doublets = {(2, 1): 3}
    triplets = {(3, 2, 1): 4, (9, 2, 1): 1}
    result = check_consistency(doublets, triplets)
    assert result.missing == {(3, 2): 4, (9, 2): 1}
    assert result.undercounted == {(2, 1): (5, 3)}
    assert result.shortfall == 4 + 1 + 2


# --- Checks on the real exports -------------------------------------------

RAW = Path(__file__).resolve().parents[1] / "data" / "raw" / "im77_rmrl"
DOUBLETS = RAW / "Doublets-GTEQ-0-results.pdf.txt"
TRIPLETS = RAW / "Triplets-GTEQ-0-results.pdf.txt"
needs_real_data = pytest.mark.skipif(
    not (DOUBLETS.exists() and TRIPLETS.exists()),
    reason="real exports not present in data/raw/im77_rmrl/ (see data/README.md)",
)


@pytest.fixture(scope="module")
def real():
    doublets = parse_report_file(str(DOUBLETS), 2)
    triplets = parse_report_file(str(TRIPLETS), 3)
    return doublets, triplets


@needs_real_data
def test_real_reports_parse_completely(real):
    doublets, triplets = real
    assert doublets.ok and doublets.declared_records == 2730
    assert triplets.ok and triplets.declared_records == 3681
    assert sum(count for _, count in doublets.rows) == 9692
    assert sum(count for _, count in triplets.rows) == 6517


@needs_real_data
def test_real_reports_match_published_landmarks(real):
    doublets, triplets = real
    pairs = dict(doublets.rows)
    # Mahadevan (1977, para. 10.13) gives 291 for the most frequent pair, which
    # sits at the right end of lines. The export has 290 for it.
    assert doublets.rows[0] == ((99, 267), 290)
    # Sign 342, the most frequent sign, stands mostly at the left end of lines:
    # it has a neighbour on its right far more often than on its left.
    has_right_neighbour = sum(c for (left, _), c in pairs.items() if left == 342)
    has_left_neighbour = sum(c for (_, right), c in pairs.items() if right == 342)
    assert (has_right_neighbour, has_left_neighbour) == (1351, 393)
    # Yadav et al. (2010) give 336, 89, 211 as the most frequent triplet of the
    # EBUDS subset, written in reading order. Printed order is the reverse.
    assert dict(triplets.rows)[(211, 89, 336)] == 44


@needs_real_data
def test_real_tables_known_disagreement_is_unchanged(real):
    """The two exports disagree slightly. Pin the size of the disagreement so
    that a corrected or different export is noticed straight away."""
    doublets, triplets = real
    result = check_consistency(dict(doublets.rows), dict(triplets.rows))
    assert result.implied_pairs == 2599
    assert len(result.missing) == 19
    assert len(result.undercounted) == 30
    assert result.shortfall == 68
