# Remaining v3 Work

## Community Self-Service

- Add voter roster management to the web UI, including ASF ID validation and a clear policy for issues added after a roster is configured.
- Add STV creation and editing for candidate labels, names, ASF IDs, and seats. The current web issue creation flow supports YNA only.
- Define delegated management semantics for `authz` before granting access beyond the election owner.
- Expose closed-election tallying through an owner-authorized workflow with execution status, failure reporting, stored results, and controlled downloads. Separate summary results from participation lists and anonymized raw ballots.
- Populate past elections in the voting dashboard and define who can view their results.

## Operations and Performance

- Define production person-directory refresh and how identity changes interact with frozen election data.
- Measure synchronous SQLite and cryptographic work in HTTP handlers before choosing an offloading strategy; keep database connections in their owning thread.
- Resolve the advertised open-election tally flag: the underlying tally currently requires a closed election. Do not bypass that state restriction as a tooling cleanup.
- Document the complete service deployment, database backup and restore procedure, and released-version pinning with Infra.

## Validation

- Run historical STV comparisons when the private meeting fixtures are available.
- Extend boundary tests alongside new self-service features; avoid replacing behavior checks with coverage targets.
