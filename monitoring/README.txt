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

We also support OpenSTV (www.openstv.org) or the deprecated VoteMain
(http://sourceforge.net/projects/votesystem) systems. Most modern
tools use the blt format.

Simply feed as input the STV-tally email (typically used for the board
elections) and direct the output to 'outputFile' (or whatever
you'd like):

   ./nstv-rank.py raw_votes.txt > outputFile

After installing Voting Systems Toolbox, you can execute the 'VoteMain'
program as

    java -cp Vote-0-4.jar VoteMain -system stv-meek -seats 9 outputFile
        or
    java -cp Quick_STV_1_2.jar VoteMain -system stv-meek -seats 9 outputFile

where outputFile is the output of nstv-rank.py above.

Using blt-oriented STV tools, such as OpenSTV:

   ./nstv-rank.py -b raw_votes.txt > outputFile.blt

and load in the blt file to OpenSTV. Please note the ASF uses Meek STV with:

    Precision: 6
    Threshold:  Droop | Dynamic | Fractional

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
