# Database Schema Documentation

This document describes the SQLite database schema for an election management system. The schema supports creating and managing elections, defining issues to vote on, tracking eligible voters, and securely recording votes. It emphasizes security through cryptographic fields (e.g., salts, hashed tokens, encrypted votes) and enforces data integrity with constraints like foreign keys and strict typing.

## Overview
The database consists of five tables:
- `election`: Stores election metadata, including ownership and cryptographic data.
- `issue`: Defines specific issues within an election, with voting mechanisms and metadata.
- `person`: Tracks individuals involved in elections (e.g., voters, owners).
- `mayvote`: Specifies which persons are eligible to vote on specific issues.
- `vote`: Records encrypted votes, supporting re-voting by tracking insertion order.

All tables use SQLite’s `STRICT` mode to enforce type constraints. The schema avoids `AUTOINCREMENT` for IDs (except in `vote`) to prevent predictable URLs, using 10-character hexadecimal IDs instead.

## Table Details

### `election`
Stores metadata for each election.

- **Columns**:
  - `eid` (TEXT, PRIMARY KEY): A 10-character hexadecimal election ID (e.g., "1a2b3c4d5e"). Not auto-incremented to prevent URL deduction. Must match the pattern `[0-9a-f]{10}`.
  - `title` (TEXT, NOT NULL): The election’s title.
  - `owner_pid` (TEXT, NOT NULL): The ID of the person who created/owns the election. References `person(pid)`.
  - `authz` (TEXT): Specifies an LDAP group (e.g., group name or identifier) allowed to edit the election. If `NULL`, only `owner_pid` can edit. The exact format is TBD but will likely map to LDAP-based persons.
  - `salt` (BLOB): A 16-byte salt generated using `secrets.token_bytes()` in Python, set when the election is opened. `NULL` if not opened.
  - `opened_key` (BLOB): A 32-byte hash (using Argon2) derived from election data to detect tampering, set when the election is opened. `NULL` if not opened.
  - `closed` (INTEGER): Indicates election status: `NULL` or `0` for not closed, `1` for closed (implies opened). Must be `NULL`, `0`, or `1`.

- **Constraints**:
  - Foreign key: `owner_pid` references `person(pid)` with `RESTRICT` on delete and `NO ACTION` on update.
  - Check constraints ensure `eid` format, `salt` (16 bytes or `NULL`), `opened_key` (32 bytes or `NULL`), and `closed` values.

### `issue`
Represents issues (questions or proposals) within an election.

- **Columns**:
  - `iid` (TEXT, PRIMARY KEY): A 10-character hexadecimal issue ID (e.g., "a1b2c3d4e5"). Must match `[0-9a-f]{10}`.
  - `eid` (TEXT, NOT NULL): The election ID this issue belongs to. References `election(eid)`.
  - `title` (TEXT, NOT NULL): A one-line title for the issue.
  - `description` (TEXT): An optional detailed description of the issue.
  - `type` (TEXT, NOT NULL): The voting mechanism. Currently supports:
    - `yna`: Yes/No/Abstain voting.
    - `stv`: Single Transferable Vote.
    Additional types may be added in the future.
  - `kv` (TEXT): JSON-formatted key-value pairs for issue-specific data, varying by `type`. For example, `stv` issues may include a `"candidates"` key listing candidate names or IDs.

- **Constraints**:
  - Foreign key: `eid` references `election(eid)` with `RESTRICT` on delete and `NO ACTION` on update.
  - Check constraint ensures `iid` format.

- **Indexes**:
  - `idx_issue_eid`: Index on `eid` for efficient lookups of issues by election.

### `person`
Stores information about individuals (voters, owners).

- **Columns**:
  - `pid` (TEXT, PRIMARY KEY): A unique person ID (e.g., LDAP username).
  - `name` (TEXT): An optional human-readable name.
  - `email` (TEXT, NOT NULL): Contact email for sending ballot links.

- **Constraints**:
  - No foreign keys or additional constraints.

### `mayvote`
Defines which persons are eligible to vote on specific issues.

- **Columns**:
  - `pid` (TEXT, NOT NULL): The person ID. References `person(pid)`.
  - `iid` (TEXT, NOT NULL): The issue ID. References `issue(iid)`.
  - `salt` (BLOB): A 16-byte salt generated using `secrets.token_bytes()`, used for generating a vote token and encryption key. `NULL` until the election is opened.

- **Constraints**:
  - Primary key: `(pid, iid)` ensures a person can be eligible for an issue only once.
  - Foreign keys: `pid` references `person(pid)`, `iid` references `issue(iid)`, both with `RESTRICT` on delete and `NO ACTION` on update.
  - Check constraint ensures `salt` is 16 bytes or `NULL`.

### `vote`
Records votes cast for issues, supporting re-voting.

- **Columns**:
  - `vid` (INTEGER, PRIMARY KEY, AUTOINCREMENT): Auto-incrementing ID to track insertion order (aliases `_ROWID_`).
  - `vote_token` (BLOB, NOT NULL): A 32-byte hash (using Argon2) of a person-issue pair (from `mayvote`), used for encryption key derivation.
  - `ciphertext` (BLOB, NOT NULL): The encrypted vote data, currently using Fernet encryption, with plans to transition to XChaCha20-Poly1305.

- **Constraints**:
  - Check constraint ensures `vote_token` is 32 bytes.
  - No foreign keys, but `vote_token` is derived from `mayvote` data.

- **Indexes**:
  - `idx_by_vote_token`: Index on `vote_token` for efficient vote lookups.

## Key Features
- **Security**:
  - Cryptographic fields ensure vote and election integrity:
    - `salt` (16 bytes) in `election` and `mayvote` uses `secrets.token_bytes()`.
    - `opened_key` (32 bytes) in `election` uses Argon2 to hash election data for tamper detection.
    - `vote_token` (32 bytes) in `vote` uses Argon2 to hash person-issue pairs.
    - `ciphertext` in `vote` uses Fernet encryption (to be replaced with XChaCha20-Poly1305).
  - Non-predictable IDs (`eid`, `iid`) use 10-character hex strings to prevent URL guessing.
- **Re-voting**: The `vote` table allows multiple votes per person-issue pair. The latest vote is identified using `MAX(vid)`, leveraging the auto-incrementing `vid`. Older votes are retained for auditing.
- **Flexible Issues**: The `issue` table supports multiple voting mechanisms (`yna`, `stv`) with extensible JSON metadata (`kv`). For example, `stv` issues may specify candidates in `kv`.
- **Data Integrity**: Foreign keys with `RESTRICT` prevent deletion of referenced records, and `STRICT` mode enforces type safety.
- **Election Lifecycle**:
  - **Editable**: The election is created and can be modified (e.g., adding issues, voters).
  - **Open**: A Python method call opens the election, setting `salt` and `opened_key`. Eligible voters (in `mayvote`) can vote on issues.
  - **Closed**: A Python method call closes the election (sets `closed = 1`), enabling tallying.
  - The owner (`owner_pid`) can monitor and edit the election at all stages, including viewing voter eligibility and vote counts.

## Notes
- **Authorization**: The `authz` field’s format is TBD but will likely use LDAP group identifiers to define editing permissions. Validation occurs outside the schema (e.g., via LDAP integration).
- **Query Optimization**: The schema references a `queries.yaml` file, which maps query names to SQL statements for all database interactions. This file provides insight into common operations (e.g., vote tallying, eligibility checks). Specific queries are not included here but can be analyzed for index optimization.
- **Future Changes**: The `ciphertext` encryption will transition from Fernet to XChaCha20-Poly1305. Additional `issue` types may be added beyond `yna` and `stv`.
