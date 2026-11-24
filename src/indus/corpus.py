"""Line-by-line texts of the Indus corpus, and sign-sequence counts made from them.

This module reads a transcription of Mahadevan's 1977 concordance that has one
row per line of text, counts adjacent sign sequences in it, and compares the
counts with the published frequency tables (see ``indus.im77_ngrams``).

Layout of the file
------------------
A CSV with the header ``ID,OBJTYPE,LOCATION,FIELDSYM,SIDE,LINE,LENGTH,SIGNS``.
``SIGNS`` holds Mahadevan sign numbers joined by hyphens, for example
``342-008-072-067-000``. ``000`` marks a sign that could not be read. A row
with an empty ``SIGNS`` field is a side of an object that carries no text.

Order of the signs
------------------
Signs are listed as printed in the concordance, left to right. Mahadevan prints
every line of text running right to left, so the LAST number is the sign that
is read FIRST. The frequency tables use the same order, which is why the two
can be compared directly.

Command line
------------
    python -m indus.corpus summary CORPUS.csv
    python -m indus.corpus compare CORPUS.csv DOUBLETS.csv TRIPLETS.csv
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from dataclasses import dataclass, field

from indus.im77_ngrams import check_consistency, load_csv

UNREAD = 0
"""Sign number used for a sign that is present on the object but not read."""


@dataclass(frozen=True)
class TextLine:
    """One line of text on one side of one object."""

    text_id: str
    object_type: str
    site: str
    field_symbol: str
    side: str
    line: str
    signs: tuple[int, ...]

    @property
    def legible(self) -> tuple[int, ...]:
        return tuple(sign for sign in self.signs if sign != UNREAD)


@dataclass
class Corpus:
    lines: list[TextLine] = field(default_factory=list)
    problems: list[tuple[str, str, str]] = field(default_factory=list)
    """(text id, what is wrong, the SIGNS field as written)."""

    @property
    def inscribed(self) -> list[TextLine]:
        """Lines that carry at least one sign, read or not."""
        return [line for line in self.lines if line.signs]


def parse_signs(raw: str) -> tuple[tuple[int, ...], bool]:
    """Turn ``"342-008-000"`` into ``(342, 8, 0)``.

    Returns the signs and whether an empty token was met (two hyphens in a
    row). An empty token becomes ``UNREAD``, so the signs on either side of it
    are never counted as neighbours.
    """
    raw = raw.strip()
    if not raw:
        return (), False
    tokens = raw.split("-")
    had_empty = any(token.strip() == "" for token in tokens)
    return tuple(int(token) if token.strip() else UNREAD for token in tokens), had_empty


def load_corpus(path: str) -> Corpus:
    """Read a corpus file. Oddities are recorded in ``problems``, not hidden."""
    corpus = Corpus()
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw = row["SIGNS"] or ""
            signs, had_empty = parse_signs(raw)
            text_id = row["ID"].strip()
            if had_empty:
                corpus.problems.append((text_id, "empty sign between two hyphens", raw))
            declared = (row.get("LENGTH") or "").strip()
            if declared.isdigit() and int(declared) != len(signs):
                corpus.problems.append(
                    (text_id, f"LENGTH says {declared}, row has {len(signs)} signs", raw)
                )
            corpus.lines.append(
                TextLine(
                    text_id=text_id,
                    object_type=row["OBJTYPE"].strip(),
                    site=row["LOCATION"].strip(),
                    field_symbol=(row.get("FIELDSYM") or "").strip(),
                    side=(row.get("SIDE") or "").strip(),
                    line=(row.get("LINE") or "").strip(),
                    signs=signs,
                )
            )
    return corpus


@dataclass
class Summary:
    texts: int
    lines_with_signs: int
    legible_signs: int
    unread_signs: int
    distinct_signs: int
    texts_by_site: dict[str, int]
    texts_by_object_type: dict[str, int]
    sign_counts: Counter


def summarise(corpus: Corpus) -> Summary:
    """Totals that can be checked against the figures printed in the book."""
    site_of: dict[str, str] = {}
    type_of: dict[str, str] = {}
    sign_counts: Counter = Counter()
    unread = 0
    for line in corpus.inscribed:
        site_of.setdefault(line.text_id, line.site)
        type_of.setdefault(line.text_id, line.object_type)
        sign_counts.update(line.legible)
        unread += len(line.signs) - len(line.legible)
    return Summary(
        texts=len(site_of),
        lines_with_signs=len(corpus.inscribed),
        legible_signs=sum(sign_counts.values()),
        unread_signs=unread,
        distinct_signs=len(sign_counts),
        texts_by_site=dict(Counter(site_of.values()).most_common()),
        texts_by_object_type=dict(sorted(Counter(type_of.values()).items())),
        sign_counts=sign_counts,
    )


def count_ngrams(lines, n: int) -> Counter:
    """Count every run of ``n`` adjacent legible signs, in printed order.

    A run that includes an unread sign is not counted, and runs never cross
    from one line to the next.
    """
    counts: Counter = Counter()
    for line in lines:
        signs = line.signs
        for start in range(len(signs) - n + 1):
            window = signs[start : start + n]
            if UNREAD not in window:
                counts[window] += 1
    return counts


def count_pairs_with_repeated_right_sign(lines) -> Counter:
    """Count pairs whose right-hand sign already stands further left in the line.

    In ``169-183-169-407`` the pair ``183 169`` is such a pair: its right-hand
    sign, 169, is also the first sign of the line.
    """
    counts: Counter = Counter()
    for line in lines:
        signs = line.signs
        for i in range(len(signs) - 1):
            left, right = signs[i], signs[i + 1]
            if UNREAD not in (left, right) and right in signs[:i]:
                counts[(left, right)] += 1
    return counts


def count_pairs_repeat_rule(lines) -> Counter:
    """Count pairs the way the IM77 doublet table appears to count them.

    Two departures from a plain count, both INFERRED by comparing a plain count
    with the table and not documented anywhere we know of:

    1. A pair is skipped when its right-hand sign already stands further left
       in the same line.
    2. A doubled sign (``a a``) is counted once per line, however often the
       doubling occurs in that line.

    Use this only to explain the table. For analysis, use ``count_ngrams``.
    """
    counts: Counter = Counter()
    for line in lines:
        signs = line.signs
        doubled_seen: set[int] = set()
        for i in range(len(signs) - 1):
            left, right = signs[i], signs[i + 1]
            if UNREAD in (left, right):
                continue
            if left == right:
                if left not in doubled_seen:
                    doubled_seen.add(left)
                    counts[(left, right)] += 1
            elif right not in signs[:i]:
                counts[(left, right)] += 1
    return counts


@dataclass
class Comparison:
    """How counts made from a corpus line up with a published table."""

    sequence_types: int
    identical: int
    only_in_table: int
    only_in_corpus: int
    corpus_above_table: int
    corpus_below_table: int
    corpus_total: int
    table_total: int


def compare_counts(corpus_counts, table) -> Comparison:
    keys = set(corpus_counts) | set(table)
    above = below = identical = 0
    for key in keys:
        mine, theirs = corpus_counts.get(key, 0), table.get(key, 0)
        if mine == theirs:
            identical += 1
        elif mine > theirs:
            above += mine - theirs
        else:
            below += theirs - mine
    return Comparison(
        sequence_types=len(keys),
        identical=identical,
        only_in_table=sum(1 for key in table if corpus_counts.get(key, 0) == 0),
        only_in_corpus=sum(1 for key in corpus_counts if table.get(key, 0) == 0),
        corpus_above_table=above,
        corpus_below_table=below,
        corpus_total=sum(corpus_counts.values()),
        table_total=sum(table.values()),
    )


@dataclass
class DisagreementExplained:
    disagreeing_pairs: int
    explained: int
    unexplained: list[tuple[int, int]]


def explain_table_disagreement(lines, doublets, triplets) -> DisagreementExplained:
    """Test the repeat rule on the pairs where the two tables disagree.

    ``check_consistency`` lists the pairs that the triplet table implies but
    the doublet table lacks or counts too low. A pair counts as explained when
    the corpus holds at least as many occurrences with a repeated right-hand
    sign as the doublet table is short by.
    """
    result = check_consistency(doublets, triplets)
    repeated = count_pairs_with_repeated_right_sign(lines)
    shortfalls = dict(result.missing)
    shortfalls.update({pair: need - have for pair, (need, have) in result.undercounted.items()})
    unexplained = sorted(pair for pair, short in shortfalls.items() if repeated[pair] < short)
    return DisagreementExplained(
        disagreeing_pairs=len(shortfalls),
        explained=len(shortfalls) - len(unexplained),
        unexplained=unexplained,
    )


def _cmd_summary(argv: list[str]) -> int:
    corpus = load_corpus(argv[0])
    summary = summarise(corpus)
    print(f"texts                 : {summary.texts}")
    print(f"lines with signs      : {summary.lines_with_signs}")
    print(f"legible sign tokens   : {summary.legible_signs}")
    print(f"unread sign tokens    : {summary.unread_signs}")
    print(f"distinct signs        : {summary.distinct_signs}")
    print(f"texts by site         : {summary.texts_by_site}")
    print(f"texts by object type  : {summary.texts_by_object_type}")
    print(f"most frequent signs   : {summary.sign_counts.most_common(5)}")
    print(f"oddities in the file  : {len(corpus.problems)}")
    for problem in corpus.problems[:20]:
        print("   ", problem)
    return 0


def _print_comparison(label: str, comparison: Comparison) -> None:
    share = comparison.corpus_total / comparison.table_total if comparison.table_total else 0
    print(f"{label}")
    print(f"    table total / corpus total : {comparison.table_total} / {comparison.corpus_total} ({share:.1%})")
    print(f"    identical counts           : {comparison.identical} of {comparison.sequence_types}")
    print(f"    only in table / in corpus  : {comparison.only_in_table} / {comparison.only_in_corpus}")
    print(f"    corpus above table by      : {comparison.corpus_above_table}")
    print(f"    corpus below table by      : {comparison.corpus_below_table}")


def _cmd_compare(argv: list[str]) -> int:
    lines = load_corpus(argv[0]).inscribed
    doublets, triplets = load_csv(argv[1]), load_csv(argv[2])
    _print_comparison("pairs, plain count", compare_counts(count_ngrams(lines, 2), doublets))
    _print_comparison("pairs, repeat rule", compare_counts(count_pairs_repeat_rule(lines), doublets))
    _print_comparison("triplets, plain count", compare_counts(count_ngrams(lines, 3), triplets))
    explained = explain_table_disagreement(lines, doublets, triplets)
    print("pairs on which the two tables disagree")
    print(f"    explained by a repeated right-hand sign : {explained.explained} of {explained.disagreeing_pairs}")
    for pair in explained.unexplained:
        print(f"    not explained: {pair}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == "summary":
        return _cmd_summary(argv[1:])
    if len(argv) == 4 and argv[0] == "compare":
        return _cmd_compare(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
