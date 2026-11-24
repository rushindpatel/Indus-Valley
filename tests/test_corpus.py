"""Tests for the corpus loader and the sign-sequence counts.

The first group uses a small made-up corpus, so it always runs. The second
group checks a private working copy of the Mahadevan 1977 texts and runs only
when that file has been placed in data/raw/m77_github_copy/ (see
data/README.md). The copy has no licence and is never committed.
"""
from pathlib import Path

import pytest

from indus.corpus import (
    UNREAD,
    compare_counts,
    count_ngrams,
    count_pairs_repeat_rule,
    count_pairs_with_repeated_right_sign,
    explain_table_disagreement,
    load_corpus,
    parse_signs,
    summarise,
)
from indus.im77_ngrams import load_csv

# Made-up texts. Sign numbers are arbitrary and stand for nothing.
SAMPLE = (
    "ID,OBJTYPE,LOCATION,FIELDSYM,SIDE,LINE,LENGTH,SIGNS\n"
    "9001,1,MD,35.0,0,0,4,003-002-001-000\n"   # ends in an unread sign
    "9002,1,HP,,0,0,4,005-004-005-006\n"       # 5 comes back after 4
    "9003,2,HP,,0,0,4,008-008-008-007\n"       # a sign doubled twice in one line
    "9003,2,HP,,1,0,0,\n"                      # a side with no text
    "9004,3,LL,,0,0,2,001--002\n"              # two hyphens in a row
    "9005,4,KB,,0,0,3,001-002\n"               # LENGTH does not match
)


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "corpus.csv"
    path.write_text(SAMPLE, encoding="utf-8")
    return load_corpus(str(path))


def test_parse_signs():
    assert parse_signs("342-008-000") == ((342, 8, UNREAD), False)
    assert parse_signs("") == ((), False)
    assert parse_signs("001--002") == ((1, UNREAD, 2), True)


def test_load_keeps_every_row_and_its_details(sample):
    assert len(sample.lines) == 6
    assert len(sample.inscribed) == 5
    first = sample.lines[0]
    assert (first.text_id, first.object_type, first.site) == ("9001", "1", "MD")
    assert first.field_symbol == "35.0"
    assert first.signs == (3, 2, 1, UNREAD)
    assert first.legible == (3, 2, 1)


def test_oddities_are_reported_not_hidden(sample):
    reported = {(text_id, what) for text_id, what, _ in sample.problems}
    assert ("9004", "empty sign between two hyphens") in reported
    assert ("9004", "LENGTH says 2, row has 3 signs") in reported
    assert ("9005", "LENGTH says 3, row has 2 signs") in reported
    assert not any(text_id in {"9001", "9002", "9003"} for text_id, _, _ in sample.problems)


def test_summary_counts_texts_once_however_many_sides(sample):
    summary = summarise(sample)
    assert summary.texts == 5
    assert summary.lines_with_signs == 5
    assert summary.legible_signs == 3 + 4 + 4 + 2 + 2
    assert summary.unread_signs == 2
    assert summary.distinct_signs == 8
    assert summary.texts_by_site == {"HP": 2, "MD": 1, "LL": 1, "KB": 1}
    assert summary.texts_by_object_type == {"1": 2, "2": 1, "3": 1, "4": 1}
    assert summary.sign_counts[8] == 3


def test_plain_counts_skip_unread_signs_and_line_breaks(sample):
    pairs = count_ngrams(sample.inscribed, 2)
    assert pairs == {
        (3, 2): 1, (2, 1): 1,              # 9001; the pair with the unread sign is skipped
        (5, 4): 1, (4, 5): 1, (5, 6): 1,   # 9002
        (8, 8): 2, (8, 7): 1,              # 9003
        (1, 2): 1,                         # 9005 only; 9004 has an unread sign between
    }
    triplets = count_ngrams(sample.inscribed, 3)
    assert triplets == {(3, 2, 1): 1, (5, 4, 5): 1, (4, 5, 6): 1, (8, 8, 8): 1, (8, 8, 7): 1}


def test_pairs_with_a_repeated_right_sign(sample):
    # 9002: in "4 5" the 5 already stands at the start of the line.
    # 9003: in the second "8 8" the 8 already stands at the start of the line.
    assert count_pairs_with_repeated_right_sign(sample.inscribed) == {(4, 5): 1, (8, 8): 1}


def test_repeat_rule_drops_repeats_and_counts_doubling_once_per_line(sample):
    pairs = count_pairs_repeat_rule(sample.inscribed)
    assert (4, 5) not in pairs
    assert pairs[(8, 8)] == 1
    assert pairs[(5, 4)] == 1 and pairs[(5, 6)] == 1 and pairs[(8, 7)] == 1
    assert sum(pairs.values()) == sum(count_ngrams(sample.inscribed, 2).values()) - 2


def test_compare_counts():
    corpus_counts = {(1, 2): 5, (2, 3): 2, (9, 9): 1}
    table = {(1, 2): 5, (2, 3): 4, (7, 7): 3}
    comparison = compare_counts(corpus_counts, table)
    assert comparison.sequence_types == 4
    assert comparison.identical == 1
    assert comparison.only_in_table == 1
    assert comparison.only_in_corpus == 1
    assert comparison.corpus_above_table == 1
    assert comparison.corpus_below_table == 2 + 3
    assert (comparison.corpus_total, comparison.table_total) == (8, 12)


def test_repeat_rule_explains_a_made_up_disagreement(sample):
    lines = sample.inscribed
    # A doublet table built with the repeat rule and a triplet table built
    # without it disagree on exactly the pair the rule dropped.
    doublets = dict(count_pairs_repeat_rule(lines))
    triplets = dict(count_ngrams(lines, 3))
    explained = explain_table_disagreement(lines, doublets, triplets)
    assert explained.disagreeing_pairs == 2
    assert explained.explained == 2
    assert explained.unexplained == []


def test_a_disagreement_with_no_repeat_stays_unexplained(sample):
    lines = sample.inscribed
    doublets = dict(count_ngrams(lines, 2))
    del doublets[(3, 2)]
    triplets = dict(count_ngrams(lines, 3))
    explained = explain_table_disagreement(lines, doublets, triplets)
    assert explained.unexplained == [(3, 2)]


# --- Checks on the private working copy ------------------------------------

ROOT = Path(__file__).resolve().parents[1] / "data"
CORPUS = ROOT / "raw" / "m77_github_copy" / "indus_corpus_alt.csv"
DOUBLETS = ROOT / "processed" / "im77_doublets.csv"
TRIPLETS = ROOT / "processed" / "im77_triplets.csv"
needs_real_data = pytest.mark.skipif(
    not (CORPUS.exists() and DOUBLETS.exists() and TRIPLETS.exists()),
    reason="private corpus copy or frequency tables not present (see data/README.md)",
)


@pytest.fixture(scope="module")
def real():
    return load_corpus(str(CORPUS)), load_csv(str(DOUBLETS)), load_csv(str(TRIPLETS))


@needs_real_data
def test_real_copy_against_the_totals_printed_in_the_book(real):
    """Mahadevan (1977) gives 2,906 texts, 3,573 lines, 13,372 sign
    occurrences and 417 signs. The copy matches on texts and signs and falls
    short on sign occurrences. Pinned so that a different copy is noticed."""
    corpus, _, _ = real
    summary = summarise(corpus)
    assert summary.texts == 2906
    assert summary.distinct_signs == 417
    assert summary.lines_with_signs == 3574
    assert summary.legible_signs == 12870
    assert summary.unread_signs == 1286
    assert summary.sign_counts.most_common(1) == [(342, 1345)]
    assert summary.texts_by_site == {
        "MD": 1540, "HP": 979, "LL": 165, "KB": 99, "CD": 72, "OS": 34, "WA": 17,
    }
    assert {text_id for text_id, _, _ in corpus.problems} == {"1030", "2084", "2632"}


@needs_real_data
def test_real_copy_against_the_frequency_tables(real):
    corpus, doublets, triplets = real
    lines = corpus.inscribed
    pairs = compare_counts(count_ngrams(lines, 2), doublets)
    assert (pairs.corpus_total, pairs.table_total) == (9271, 9692)
    assert (pairs.identical, pairs.sequence_types) == (2328, 2757)
    assert (pairs.corpus_above_table, pairs.corpus_below_table) == (92, 513)
    threes = compare_counts(count_ngrams(lines, 3), triplets)
    assert (threes.corpus_total, threes.table_total) == (6124, 6517)
    assert (threes.identical, threes.sequence_types) == (3298, 3709)


@needs_real_data
def test_real_copy_supports_the_repeat_rule(real):
    """The repeat rule removes nearly every case where the copy has MORE of a
    pair than the doublet table, and accounts for 47 of the 49 pairs on which
    the doublet and triplet tables disagree."""
    corpus, doublets, triplets = real
    lines = corpus.inscribed
    with_rule = compare_counts(count_pairs_repeat_rule(lines), doublets)
    assert with_rule.corpus_above_table == 3
    assert with_rule.only_in_corpus == 1
    explained = explain_table_disagreement(lines, doublets, triplets)
    assert (explained.explained, explained.disagreeing_pairs) == (47, 49)
    assert explained.unexplained == [(192, 342), (387, 59)]
