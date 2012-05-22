Included are some helpful tools/scripts to make the
vote monitor's job easier.

When votes are closed, each monitor will get, via EMail,
a final tally (list) of all votes cast, with hash ID and
timestamp. The list is time-ordered as well, so the later
cast ballot are later on in the tally (closer to the bottom).

For STV, we use voter/stv_tool.py to process the vote results:

    ./stv_tool.py raw_votes.txt

where raw_votes.txt is emailed set of votes. For examples,
see Meetings/.../raw_board_votes.txt. Lines other than votes
are ignored, and the votes are assumed to be time-ordered to
ensure that only the latest vote is considered.


----

For simple YNA votes (Yes / No / Abstain), we have

    yna-summary.pl

which does the checks for you.

This script is smart enough that you can actually concat
*all* the final vote tallies for yna elections into 1 big
file, and it will pull out the issue name and the results
for each issue.

   ./yna-summary.pl all30tally.txt

yna-summary.pl will only honor the last vote count per voter.


----

Also see monitoring-check.pl to ensure the incoming votes are
legitimate voters.
