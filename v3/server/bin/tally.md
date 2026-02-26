# Tally Script Runbook

## Overview
The `tally.py` script is used by administrators to tally votes for all issues in a selected election. It is designed to be run interactively from the command line on the server. Results are output in text or JSON format.

## Usage
Run the script with `uv run --script tally.py [options]`.

### Options
- `--spy-on-open-elections`: Allow tallying of open elections. This is a long flag to ensure intentional use. Use with extreme caution, as it may expose incomplete or sensitive data.
- `--election-id <EID>`: Specify the election ID directly to skip interactive selection.
- `--db-path <PATH>`: Path to the database file (default: `../steve.db` relative to the script).
- `--output <FORMAT>`: Output format, either `text` (default) or `json`.

### Interactive Mode
If `--election-id` is not provided:
1. The script lists available elections (closed by default, or open if `--spy-on-open-elections` is used).
2. Elections are sorted by close date (most recent first).
3. The admin is prompted to select an election by number.
4. Type 'q' to quit without selecting.

### Process
1. If tampering is detected (via `election.is_tampered()`), the script fails with an error.
2. For each issue in the election, votes are tallied using `election.tally_issue()`.
3. Results are output in the specified format.
4. Any exception during tallying causes the script to fail hard (no recovery).

## Output Formats
- **Text**: Human-readable format with issue details, results, and supporting data.
- **JSON**: Structured data for integration with other tools.

## Security and Concerns
- **Misuse**: This script can reveal vote results prematurely if used with `--spy-on-open-elections`. There are no built-in restrictions on who can run it—ensure only trusted admins have access. Consider OS-level permissions or environment checks.
- **Performance**: Tallying is intentionally slow due to cryptographic operations to protect voter privacy. Do not expect web-like response times; run in a background process if needed.
- **Logging**: No internal logging is performed, as it could be tampered with. Results are only output to stdout/stderr.
- **Tampering**: Elections are checked for tampering before tallying. If tampered, the script exits with an error.
- **Errors**: All exceptions are allowed to propagate and crash the script. Fix issues and retry.

## Examples
- Tally a specific closed election: `./tally.py --election-id ABC123`
- Spy on an open election: `./tally.py --spy-on-open-elections --election-id DEF456`
- Interactive with JSON output: `./tally.py --output json`

## TODO
- Add unit and integration tests for tallying logic, edge cases (e.g., no votes, mixed vtypes), and CLI behavior.
- Consider adding progress indicators for large elections.
- Evaluate automating tally runs post-election closure.
