"""Sign-pair and sign-triplet frequency tables from Mahadevan's 1977 concordance.

The Indus Research Centre site (indusscript.in) serves "IM77 Frequency Tables"
as PDF reports. Saved as text, a report alternates between a line of Mahadevan
sign numbers and a line holding how often that sequence occurs. A four-line
header opens the report and a three-line header repeats at every page break.

Order of the signs
------------------
Each row lists the signs in the order they are printed in the concordance,
left to right. Mahadevan prints every line of text running right to left, so
the LAST number in a row is the sign that is read FIRST. Use
``load_csv(path, reading_order=True)`` to get rows in reading order.

Command line
------------
    python -m indus.im77_ngrams parse REPORT.txt N OUT.csv
    python -m indus.im77_ngrams check DOUBLETS.csv TRIPLETS.csv

``parse`` exits with status 1 if anything in the report does not fit the
expected layout, so a silent mis-parse is not possible.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from dataclasses import dataclass, field

_HEADER_PATTERNS = (
    re.compile(r"^IM77RMRL$"),
    re.compile(r"^IM77 Frequency Tables$"),
    re.compile(r"^\w+ frequencies\b", re.I),
)
_RECORDS_FOUND = re.compile(r"^(\d+)\s*records found$", re.I)

_POSITION_NAMES = {
    1: ("sign",),
    2: ("left_sign", "right_sign"),
    3: ("left_sign", "middle_sign", "right_sign"),
}


def column_names(n: int) -> tuple[str, ...]:
    """Column names for an n-sign table, in printed (left to right) order."""
    return _POSITION_NAMES.get(n) or tuple(f"sign_{i + 1}_from_left" for i in range(n))


@dataclass
class ParsedReport:
    n: int
    declared_records: int | None
    rows: list[tuple[tuple[int, ...], int]] = field(default_factory=list)
    problems: list[tuple[int, str, str]] = field(default_factory=list)

    @property
    def duplicates(self) -> list[tuple[int, ...]]:
        counts = Counter(signs for signs, _ in self.rows)
        return [signs for signs, seen in counts.items() if seen > 1]

    @property
    def ok(self) -> bool:
        return (
            self.declared_records == len(self.rows)
            and not self.problems
            and not self.duplicates
        )


def parse_report(lines, n: int) -> ParsedReport:
    """Parse the text of one frequency report.

    ``lines`` is any iterable of text lines. Every line must be a header, a
    row of ``n`` sign numbers, or the count that follows such a row. Anything
    else is recorded in ``problems`` instead of being skipped quietly.
    """
    report = ParsedReport(n=n, declared_records=None)
    pending: tuple[int, tuple[int, ...]] | None = None
    for lineno, raw in enumerate(lines, 1):
        line = raw.replace("\x0c", "").strip()
        if not line:
            continue
        match = _RECORDS_FOUND.match(line)
        if match:
            report.declared_records = int(match.group(1))
            continue
        if any(p.match(line) for p in _HEADER_PATTERNS):
            continue
        parts = line.split()
        if not all(part.isdigit() for part in parts):
            report.problems.append((lineno, "not a row of numbers", line))
            continue
        if pending is None:
            if len(parts) != n:
                report.problems.append((lineno, f"expected {n} sign numbers", line))
                continue
            pending = (lineno, tuple(int(part) for part in parts))
        else:
            if len(parts) != 1:
                report.problems.append((lineno, "expected a single count", line))
                pending = None
                continue
            report.rows.append((pending[1], int(parts[0])))
            pending = None
    if pending is not None:
        report.problems.append((pending[0], "sign row without a count", str(pending[1])))
    return report


def parse_report_file(path: str, n: int) -> ParsedReport:
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        return parse_report(handle, n)


def write_csv(report: ParsedReport, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(column_names(report.n) + ("count",))
        for signs, count in report.rows:
            writer.writerow(signs + (count,))


def load_csv(path: str, reading_order: bool = False) -> dict[tuple[int, ...], int]:
    """Load a table written by ``write_csv`` as ``{signs: count}``.

    With ``reading_order=True`` each key is reversed, so the first element is
    the sign that is read first (the rightmost sign as printed).
    """
    table: dict[tuple[int, ...], int] = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            signs = tuple(int(value) for value in row[:-1])
            if reading_order:
                signs = signs[::-1]
            table[signs] = int(row[-1])
    return table


@dataclass
class ConsistencyResult:
    implied_pairs: int
    missing: dict[tuple[int, int], int]
    undercounted: dict[tuple[int, int], tuple[int, int]]

    @property
    def shortfall(self) -> int:
        """Smallest number of pair occurrences the doublet table must be missing."""
        return sum(self.missing.values()) + sum(
            need - have for need, have in self.undercounted.values()
        )


def check_consistency(doublets, triplets) -> ConsistencyResult:
    """Compare a doublet table with a triplet table built from the same texts.

    Every triplet ``a b c`` contains the pairs ``a b`` and ``b c``. Summed over
    all triplets, each pair must therefore occur in the doublet table at least
    as often as it opens a triplet, and at least as often as it closes one.
    """
    opens: Counter = Counter()
    closes: Counter = Counter()
    for (a, b, c), count in triplets.items():
        opens[(a, b)] += count
        closes[(b, c)] += count
    missing: dict[tuple[int, int], int] = {}
    undercounted: dict[tuple[int, int], tuple[int, int]] = {}
    pairs = set(opens) | set(closes)
    for pair in sorted(pairs):
        need = max(opens[pair], closes[pair])
        have = doublets.get(pair, 0)
        if have == 0:
            missing[pair] = need
        elif have < need:
            undercounted[pair] = (need, have)
    return ConsistencyResult(len(pairs), missing, undercounted)


def _cmd_parse(argv: list[str]) -> int:
    path, n, out = argv[0], int(argv[1]), argv[2]
    report = parse_report_file(path, n)
    write_csv(report, out)
    print(f"declared records : {report.declared_records}")
    print(f"parsed records   : {len(report.rows)}")
    print(f"total occurrences: {sum(count for _, count in report.rows)}")
    print(f"layout problems  : {len(report.problems)}")
    for problem in report.problems[:20]:
        print("   ", problem)
    print(f"duplicate rows   : {len(report.duplicates)}")
    print("RESULT:", "PASS" if report.ok else "FAIL")
    return 0 if report.ok else 1


def _cmd_check(argv: list[str]) -> int:
    result = check_consistency(load_csv(argv[0]), load_csv(argv[1]))
    print(f"pairs implied by the triplet table : {result.implied_pairs}")
    print(f"absent from the doublet table      : {len(result.missing)}")
    for pair, need in sorted(result.missing.items(), key=lambda kv: -kv[1]):
        print(f"    {pair} needed at least {need}")
    print(f"present but counted too low        : {len(result.undercounted)}")
    for pair, (need, have) in sorted(
        result.undercounted.items(), key=lambda kv: kv[1][1] - kv[1][0]
    ):
        print(f"    {pair} needed at least {need}, table has {have}")
    print(f"minimum shortfall in occurrences   : {result.shortfall}")
    agree = not result.missing and not result.undercounted
    print("RESULT:", "CONSISTENT" if agree else "INCONSISTENT")
    return 0 if agree else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 4 and argv[0] == "parse":
        return _cmd_parse(argv[1:])
    if len(argv) == 3 and argv[0] == "check":
        return _cmd_check(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
