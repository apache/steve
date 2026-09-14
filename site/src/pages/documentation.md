---
title: Documentation
description: Guides and source references for the Apache STeVe v3 application and STV tally tools.
---

# Documentation

The guides live alongside the code so that implementation details and setup instructions can be updated together.

## v3 voting application

- [Getting Started Guide](https://github.com/apache/steve/blob/trunk/v3/docs/quickstart.md) — prepare a local development environment.
- [Architecture and data model](https://github.com/apache/steve/blob/trunk/v3/README.md) — elections, people, issues, votes, and ballot storage.
- [Database schema](https://github.com/apache/steve/blob/trunk/v3/docs/schema.md) — the SQLite tables and their relationships.
- [Testing guide](https://github.com/apache/steve/blob/trunk/v3/tests/README.md) — run the application tests.

### Voting methods

The current v3 application implements two voting types:

| Method                         | How it is used                                                                                     |
| ------------------------------ | -------------------------------------------------------------------------------------------------- |
| Single Transferable Vote (STV) | Voters rank candidates. The Meek STV engine counts the ballots for the configured number of seats. |
| Yes / No / Abstain (YNA)       | Voters choose yes, no, or abstain on an issue.                                                     |

See the [voting implementations](https://github.com/apache/steve/tree/trunk/v3/steve/vtypes) for the supported options and tally behavior.

## Tally and what-if tools

The [monitoring tools guide](https://github.com/apache/steve/blob/trunk/monitoring/README.md) covers tally input formats and command-line tools. The v3 STV implementation and the what-if tool share the Meek STV engine in `monitoring/stv_tool.py`.

The [STV tally and what-if examples](https://github.com/apache/steve#stv-tally-and-what-if) show how to change the seat count, exclude a candidate, or select a runoff field. For new tallies, use the v3 `vote-results.json` export.

## Contribute a change

Open a pull request against the [`trunk` branch](https://github.com/apache/steve). For Python changes, follow the formatting, linting, and type-checking instructions in [`AGENTS.md`](https://github.com/apache/steve/blob/trunk/AGENTS.md).

Website sources are in [`site/`](https://github.com/apache/steve/tree/trunk/site). The site README explains how to build the website and preview a change.

For design discussions or questions about the code, join the [community](/community/).
