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

- Ensure the `stv_tool` module is available at `../../../monitoring/stv_tool.py` (relative to `v3/steve/vtypes/stv.py`).

### Scripts

- `populate_v2_stv.sh`: Generates test data directories with `raw_board_votes.txt` and `board_nominations.ini` files.
- `run_stv.py`: Runs the STV tally on a given meeting directory (e.g., `Meetings/yyyymmdd`).
- `check_stv_outputs.sh`: Compares the sorted outputs from two directories created by `populate_v2_stv.sh`.

### Workflow

1. Run `populate_v2_stv.sh` to create two test data directories (e.g., `dir1` and `dir2`).
2. For each directory, run `run_stv.py` on the meeting subdirectories to generate outputs.
3. Use `check_stv_outputs.sh` to verify that the outputs from `dir1` and `dir2` are pairwise equal after sorting.

### Dependencies

- `raw_board_votes.txt`: Contains the raw vote data.
- `board_nominations.ini`: Contains the label mappings for candidates.

### Importing stv_tool

The `stv.py` module imports `stv_tool` from `../../../monitoring/stv_tool.py` using dynamic loading to ensure compatibility.
