# Vote monitoring tools

Helpers for processing closed-election tallies.

When votes are closed, each monitor historically received an email: a final list of votes with hash ID and timestamp, time-ordered so later ballots sit at the bottom.

## STV (`stv_tool.py`)

Meek STV engine plus `LoadData` (load a **file**, not a directory). v3 (`steve.vtypes.stv`) and `whatif.py` (repo root) call this module.

```shell
./stv_tool.py vote-results.json
./stv_tool.py -s 9 -v raw_board_votes.txt
```

| Input                                                     | Behavior                                                                                              |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `vote-results.json` (v3 tally JSON)                       | Source of truth. `labelmap` + votestrings for the STV issue.                                          |
| `raw_board_votes.txt` (+ sibling `board_nominations.ini`) | Old-school emailed format. Non-vote lines ignored; later vote per 32-char hash wins. Warns on stderr. |
| `raw_board_votes.json` (v2 export, labels like `AA`/`AB`) | Not a tally format. Warns and exits. Keep for posterity; pass txt or v3 JSON instead.                 |

`whatif.py` runs seat / drop / runoff scenarios on the same loaders. `whatif.rb` still wants txt+ini.

## Other STV tools

OpenSTV or the deprecated VoteMain systems. Most modern tools use BLT.

Feed the STV-tally email and write an output file:

```shell
./nstv-rank.py raw_votes.txt > outputFile
```

After installing Voting Systems Toolbox:

```shell
java -cp Vote-0-4.jar VoteMain -system stv-meek -seats 9 outputFile
java -cp Quick_STV_1_2.jar VoteMain -system stv-meek -seats 9 outputFile
```

BLT-oriented tools such as OpenSTV:

```shell
./nstv-rank.py -b raw_votes.txt > outputFile.blt
```

ASF Meek STV settings: precision 6; threshold Droop | Dynamic | Fractional.

## YNA

`yna-summary.pl` tallies Yes / No / Abstain. You can concatenate all final YNA tallies into one file; it pulls out each issue name and result, honoring only the most recent vote per voter.

```shell
./yna-summary.pl all30tally.txt
```

## Voter checks

`monitoring-check.pl` checks that incoming votes are from legitimate voters.
