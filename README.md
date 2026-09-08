# Welcome to Apache Steve <http://steve.apache.org/>

Apache Steve is software to conduct a vote using the STV (Single
Transferable Vote) and other voting algorithms. The tool grew out of the voting
system used to elect the Apache Software Foundation Board of
Directors.

Read more about STV at
http://en.wikipedia.org/wiki/Single_transferable_vote

> [!NOTE]
>
> The `v3` directory contains the current (ongoing) version of Steve.
> Read the [v3/README.md](v3/README.md) file for more information about
> this version. Read the [Getting Started Guide](v3/docs/quickstart.md)
> to set up a development environment for v3.

## STV tally and what-if

Meek STV lives in [`monitoring/stv_tool.py`](monitoring/stv_tool.py).
v3 tallies (`steve.vtypes.stv`) and the what-if CLI both call that module.

**Load a vote file** with `LoadData.from_path` (a file, not a directory):

| Input | Behavior |
|---|---|
| `vote-results.json` (v3 tally JSON) | Source of truth. No warning. |
| `raw_board_votes.txt` (+ sibling `board_nominations.ini`) | Old-school. Warns on stderr. |
| `raw_board_votes.json` (v2 export) | Not a tally format. Warns and exits. |

```
python3 monitoring/stv_tool.py path/to/vote-results.json
python3 monitoring/stv_tool.py -s 9 -v path/to/raw_board_votes.txt
```

**What-if scenarios** (seats, drop a candidate, runoff-only set) are
[`whatif.py`](whatif.py). The positional argv is fixed for `whatif.rb`:

```
python3 whatif.py [-v] VOTES_FILE [seats] [name ...]
python3 whatif.py VOTES_FILE -Lastname
```

Names may be first, last, or compacted full name (case-insensitive).
A leading `-` on a name removes that candidate; otherwise only the
named candidates run. Warnings for legacy files go to stderr so they
do not break `whatif.rb` grepping of `elected` lines.

`whatif.rb` still consumes `raw_board_votes.txt`. Do not point it at
v2 JSON. Prefer `vote-results.json` for new tallies.

See also [`monitoring/README.md`](monitoring/README.md).

## Getting Started

Getting Started documentation can be found at: http://steve.apache.org/demo.html
Otherwise, come to the #steve channel on the Slack workspace at the-asf.slack.com, 
and we'd be glad to help you.

## Documentation

Documentation may be found at http://steve.apache.org/documentation.html

Contributions to the documentation are very welcome.

## Mailing Lists

Discussion about Steve takes place on the following mailing lists:

    dev@steve.apache.org    - About using Steve and developing Steve

Notification on all code changes are sent to the following mailing list:

    commits@steve.apache.org

The mailing lists are open to anyone and publicly archived.

You can subscribe the mailing lists by sending a message to
`<LIST>-subscribe@steve.apache.org` (for example
`dev-subscribe@steve.apache.org`).  To unsubscribe, send a message to
`<LIST>-unsubscribe@steve.apache.org`.  For more instructions, send a
message to `<LIST>-help@steve.apache.org`.

## Issue Tracker

If you encounter errors in Steve or want to suggest an improvement or a new
feature, please visit the Steve issue tracker at
https://github.com/apache/steve/issues
