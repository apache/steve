---
title: Get started
description: Set up a development environment for Apache STeVe v3 or work with the STV tally tools.
---

# Get started

Apache STeVe is a collection of voting tools. Start with the v3 application to work on elections and ballots, or use the tally tools to explore results from a closed election.

## Set up the v3 application

Current application development happens in the [`v3/` directory](https://github.com/apache/steve/tree/trunk/v3). It uses Python, uv, and SQLite.

Follow the [v3 Getting Started Guide](https://github.com/apache/steve/blob/trunk/v3/docs/quickstart.md) for the complete setup, including dependencies, the database, test data, configuration, and development certificates.

The guide describes a development environment. The ASF deployment also uses ASF-specific authentication and configuration; discuss deployment questions on the [development mailing list](/community/#mailing-lists).

## Work with STV results

The [monitoring tools](https://github.com/apache/steve/blob/trunk/monitoring/README.md) include the shared Meek STV tally engine. Use a v3 `vote-results.json` file for new tallies:

```shell
python3 monitoring/stv_tool.py path/to/vote-results.json
```

The [`whatif.py` tool](https://github.com/apache/steve#stv-tally-and-what-if) explores different seat counts and candidate selections. Its documentation also explains which historical ballot formats are supported.

## Find your next step

- [Documentation](/documentation/) links to the data model, testing guide, and voting implementations.
- [Community](/community/) explains how to ask questions, report issues, and contribute.
- [Downloads](/downloads/) describes release availability and how to get the development source.
