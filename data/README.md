# Data

Third-party data is not stored in this repository yet. `data/raw/` and
`data/processed/` are ignored by git until the terms of use of each source
have been confirmed. This file records where every dataset comes from and how
to rebuild it, so the work stays reproducible.

## IM77 sign-pair and sign-triplet frequency tables

| | |
|---|---|
| Source | Indus Research Centre, Roja Muthiah Research Library, Chennai: indusscript.in, "IM77 Frequency Tables" |
| Underlying work | I. Mahadevan, *The Indus Script: Texts, Concordance and Tables* (Archaeological Survey of India, 1977) |
| Retrieved | Exported by hand as PDF reports, saved as text, received 24 November 2026 |
| Queries | "Doublets frequencies greater than 0" (2,730 records), "Triplets frequencies greater than 0" (3,681 records) |

### How to rebuild

1. Put the two exported text files in `data/raw/im77_rmrl/` under these names:
   `Doublets-GTEQ-0-results.pdf.txt` and `Triplets-GTEQ-0-results.pdf.txt`.
2. Run:

   ```
   PYTHONPATH=src python -m indus.im77_ngrams parse data/raw/im77_rmrl/Doublets-GTEQ-0-results.pdf.txt 2 data/processed/im77_doublets.csv
   PYTHONPATH=src python -m indus.im77_ngrams parse data/raw/im77_rmrl/Triplets-GTEQ-0-results.pdf.txt 3 data/processed/im77_triplets.csv
   PYTHONPATH=src python -m indus.im77_ngrams check data/processed/im77_doublets.csv data/processed/im77_triplets.csv
   ```

SHA-256 of the files used so far:

```
baeaf471196bad5e293c1f9a45ad88641af2ed50ffe8a8107c7149a5c1c7f8f2  Doublets-GTEQ-0-results.pdf.txt
325189df48db8fa973947da27a53bdbfdb3850e8ed8ce347203923093fc97089  Triplets-GTEQ-0-results.pdf.txt
cacd93bd066d5e6b24d906fa9748bcc84209b57ad74dbb0093a9f139d7f0a51e  im77_doublets.csv
2754a84d64c4a84033c955f616e2b5704bdc538342c625bb9bbef68e58d8ea19  im77_triplets.csv
```

### What the tables contain

Each row is a sequence of two or three adjacent signs, identified by their
numbers in Mahadevan's sign list (1 to 417), and the number of times that
sequence occurs in the concordance.

| Table | Distinct sequences | Total occurrences | Distinct signs |
|---|---|---|---|
| Doublets | 2,730 | 9,692 | 394 |
| Triplets | 3,681 | 6,517 | 370 |

They do not contain the inscriptions themselves, the find site, the type of
object, single-sign frequencies, or the position of a sequence in its line.

### Order of the signs

A row lists the signs as printed in the concordance, left to right. Mahadevan
prints every line running right to left (1977, para. 13.2), so the last number
in a row is the sign read first. The CSV columns are named `left_sign`,
`middle_sign` and `right_sign` to keep this explicit, and
`load_csv(path, reading_order=True)` returns rows in reading order.

This was checked against two published statements:

- Mahadevan (1977, para. 10.13): the most frequent pair occurs 291 times and
  sits mostly at the right end of lines; the most frequent sign occurs 1,395
  times, 931 of them at the left end. In the export the top row is `99 267`
  with 290, and sign 342 has a right-hand neighbour 1,351 times but a
  left-hand neighbour only 393 times.
- Yadav et al. (2010, PLoS ONE 5(3): e9506) give `336, 89, 211` as the most
  frequent triplet of their EBUDS subset, written in reading order. The export
  has `211 89 336` with 44.

### Known problems

1. **The two tables do not fully agree.** Every triplet `a b c` contains the
   pairs `a b` and `b c`, so the doublet table can be checked against the
   triplet table. Of the 2,599 pairs that the triplets imply, 19 are absent
   from the doublet table and 30 are counted too low. The doublet table is
   short by at least 68 occurrences (0.7%). The largest case is the triplet
   `183 169 407` (10 occurrences) while the pair `183 169` is not listed at
   all. The cause cannot be settled without the inscriptions themselves.
   `tests/test_im77_ngrams.py` pins these numbers so that a changed export is
   noticed.
2. **Top pair is 290, not 291.** One occurrence fewer than the printed figure.
3. **23 sign numbers never appear in a pair:** 31, 44, 85, 88, 115, 118, 144,
   165, 220, 232, 235, 266, 269, 317, 346, 362, 363, 374, 377, 378, 392, 405,
   408. Whether each occurs only alone, only next to damaged signs, or not at
   all in this electronic version is not known yet.

Treat these tables as a cross-check for statistics computed from the full
texts, not as ground truth.
