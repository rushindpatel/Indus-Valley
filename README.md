# Indus-Valley

Code and data notes for an attempt at the Indus script: build a clean corpus,
reproduce the published statistics, then test hypotheses against data held
back for that purpose.

The script is undeciphered and a full decipherment is unlikely. The aim is
work that is honest about that: every step has a check that can fail, failed
steps are kept on record, and nothing is claimed that the data does not show.

## Layout

```
src/indus/     analysis code
tests/         tests; run them before trusting any number
data/          where datasets come from and how to rebuild them (data/README.md)
```

## Running the tests

```
python -m pip install pytest
python -m pytest
```

Tests that need third-party data are skipped until the files are placed as
described in `data/README.md`.

## Ground rules

1. Write the success check for a step before running it.
2. Keep a share of the data untouched for final tests.
3. Compare every result with a shuffled or random baseline.
4. Anyone should be able to rerun a result from the files here.
5. Negative results stay in the record.
