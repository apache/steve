# Testing

This directory contains scripts and utilities for testing the v3 codebase.

## Code Coverage Testing

To run code coverage testing, use the `check_coverage.py` script. This script uses the `coverage` library to measure code coverage of the `steve` package.

### Prerequisites

- Install the `coverage` library: `pip install coverage`
- Install the `faker` package: `pip install faker`

### Usage

Run the script from the `v3/tests/` directory:

```bash
python check_coverage.py
```

This will generate a coverage report in the terminal and create an HTML report in the `covreport/` directory.

## STV Testing

STV (Single Transferable Vote) testing involves running the STV tally process on sample data and verifying the results.

### Prerequisites

- Ensure the `stv_tool` module is available at `../../../monitoring/stv_tool.py` (relative to `v3/steve/vtypes/stv.py`). Live tallies prefer v3 `vote-results.json` via `LoadData.from_path`. These regression tests still use historical `raw_board_votes.txt` so v3 continues to match pre-v3 Meek results (the loader will warn that txt is old-school).
- Provide a `Meetings` directory containing subdirectories (e.g., `yyyymmdd`) with `raw_board_votes.txt` and `board_nominations.ini`.

### Scripts

- `populate_v2_stv.sh`: Generates two output directories (`v2-stv-ref` and `v3-stv`) by processing all meeting subdirectories in the provided `Meetings` directory. For each meeting, it runs the reference STV tool to produce output in `v2-stv-ref` and runs `run_stv.py` to produce output in `v3-stv`.
- `run_stv.py`: Runs the STV tally on a given meeting directory (e.g., `Meetings/yyyymmdd`).
- `check_stv_outputs.sh`: Compares the sorted outputs from the `v2-stv-ref` and `v3-stv` directories created by `populate_v2_stv.sh`.

### Workflow

1. Run `populate_v2_stv.sh` with the path to the `Meetings` directory (e.g., `populate_v2_stv.sh /path/to/Meetings`). This creates the `v2-stv-ref` and `v3-stv` directories and populates them with outputs for each meeting subdirectory.
2. Use `check_stv_outputs.sh` to verify that the outputs in `v2-stv-ref` and `v3-stv` are pairwise equal after sorting. It will report mismatches if any.

### Dependencies

- `raw_board_votes.txt`: Historical raw vote data in each meeting subdirectory (legacy format; `read_votefile` takes only the filename).
- `board_nominations.ini`: Letter-to-name map for those txt files.
- Do not pass v2 `raw_board_votes.json` into `stv_tool`; it is not a tally format.

### Importing stv_tool

The `stv.py` module imports `stv_tool` from `../../../monitoring/stv_tool.py` using dynamic loading. Tally math is `run_stv`; file loading for new code is `LoadData.from_path`. See also [`monitoring/README.md`](../../monitoring/README.md).
