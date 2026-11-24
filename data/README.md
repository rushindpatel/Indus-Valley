# Data

Third-party data is not stored in this repository. `data/raw/` and
`data/processed/` are ignored by git, and the files are kept in private
project storage. This file records where every dataset comes from and how to
rebuild it, so the work stays reproducible.

Permissions as of 24 November 2026:

- **indusscript.in exports.** The Roja Muthiah Research Library has given the
  project owner permission to use the data for non-commercial purposes. The
  owner has chosen to keep the exports private all the same. Work that uses
  them should acknowledge the Indus Research Centre, Roja Muthiah Research
  Library, Chennai.
- **Private copy of the Mahadevan 1977 texts.** No licence. It must stay
  private.

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
   all. `tests/test_im77_ngrams.py` pins these numbers so that a changed
   export is noticed. A probable cause is described under "The repeat rule"
   below: 47 of the 49 pairs are explained by it.
2. **Top pair is 290, not 291.** One occurrence fewer than the printed figure.
3. **23 sign numbers never appear in a pair:** 31, 44, 85, 88, 115, 118, 144,
   165, 220, 232, 235, 266, 269, 317, 346, 362, 363, 374, 377, 378, 392, 405,
   408. Whether each occurs only alone, only next to damaged signs, or not at
   all in this electronic version is not known yet.

Treat these tables as a cross-check for statistics computed from the full
texts, not as ground truth.

## Mahadevan 1977 texts: private working copy

| | |
|---|---|
| Source | `data/txt/indus_corpus_alt.csv` in the public GitHub repository `toddcolsen/indus_script`, branch `main` |
| Underlying work | I. Mahadevan, *The Indus Script: Texts, Concordance and Tables* (Archaeological Survey of India, 1977) |
| Retrieved | 24 November 2026, unmodified |
| Licence | **None stated.** The file must not be committed here or shared. |
| Standing | Unverified secondary copy. Who typed it in, and from which printing, is not stated. |

SHA-256 of the file used:

```
24eccb275b2a3c38655fbdf266848762361e8de04d960bc2375bb3b823652b41  indus_corpus_alt.csv
```

### How to rerun the checks

1. Put the file in `data/raw/m77_github_copy/indus_corpus_alt.csv`.
2. Build the frequency tables as described above.
3. Run:

   ```
   PYTHONPATH=src python -m indus.corpus summary data/raw/m77_github_copy/indus_corpus_alt.csv
   PYTHONPATH=src python -m indus.corpus compare data/raw/m77_github_copy/indus_corpus_alt.csv data/processed/im77_doublets.csv data/processed/im77_triplets.csv
   ```

### What the file contains

One row per line of text, 3,611 rows: Mahadevan's text number, object type,
site, field symbol, side, line, and the signs of that line as Mahadevan sign
numbers joined by hyphens, in printed left-to-right order. `000` marks a sign
that was not read. The layout is described in `src/indus/corpus.py`.

### How well it matches the book

| Measure | Book | This copy |
|---|---|---|
| Texts | 2,906 | 2,906 |
| Lines of text | 3,573 | 3,574 |
| Distinct signs | 417 | 417 |
| Legible sign occurrences | 13,372 | 12,870 (502 short, 3.8%) |
| Occurrences of sign 342 | 1,395 | 1,345 |
| Texts from Harappa / Chanhudaro | 985 / 66 | 979 / 72 |
| Texts from the other five site groups | as printed | identical |

The copy also holds 1,286 signs coded as not read. A likely reason for the
missing 502 is that the copy blanks signs the book prints as doubtful, which
the book still counts. This has not been confirmed against the printed texts.

### How well it matches the frequency tables

| | Table | Plain count from this copy | Sequence types with identical counts |
|---|---|---|---|
| Pairs | 9,692 occurrences | 9,271 (95.7%) | 2,328 of 2,757 (84%) |
| Triplets | 6,517 occurrences | 6,124 (94.0%) | 3,298 of 3,709 (89%) |

### The repeat rule

Where the copy has more of a pair than the doublet table (92 occurrences),
nearly all cases follow one pattern. The table appears to:

1. skip a pair when its right-hand sign already stands further left in the
   same line, and
2. count a doubled sign once per line, however often it is doubled there.

Counting the copy this way (`count_pairs_repeat_rule`) leaves 3 occurrences
above the table instead of 92. It also accounts for 47 of the 49 pairs on
which the doublet and triplet tables disagree. The pairs `192 342` and
`387 59` are not explained. Example: ten lines read
`169-183-169-407-089-336-065`; the pair `183 169` is absent from the doublet
table, while the triplet `183 169 407` is listed 10 times.

The rule is inferred, not documented, and it was inferred from an unverified
copy. The triplet table shows the same effect only in part. Treat it as a
lead to confirm against verified texts.

### Known faults in the copy

- Text 2632 has two hyphens in a row: a sign is missing.
- Texts 1030 and 2084 have a `LENGTH` that does not match their signs.
- 37 rows carry no signs (sides of objects without text).

### What it may be used for

Building and testing code, and first-pass statistics by site and object type.
No number from this copy goes into anything published. Published results must
come from a verified source.
