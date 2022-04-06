Title: Vote Types


<h2 id="yna">Single motion voting (Yes/No/Abstain)</h2>

This is a simple tally vote. Voters can vote either Yes or No on an
issue, or they can abstain.  Votes are tallied, and the result is
presented. It is up to the election committee to interpret the result.

----

<h2 id="ap">Apache-style Single motion voting (Yes/No/Abstain with binding votes)</h2>

This is a simple tally vote. Voters can vote either Yes or No on an
issue, or they can abstain, however certain people (committee members,
for instance) may cast binding votes whereas others may only cast
non-binding votes.  Votes are tallied, and the result is presented. It
is up to the election committee to interpret the result.

----

<h2 id="fpp">First Past the Post (presidential election style)</h2>

FPP is a voting system with multiple candidates. The candidate with
the most votes will win, regardless of whether they received more than
half the votes or not.

----


<h2 id="stv">Single Transferable Vote</h2>

The single transferable vote (STV) system is designed to achieve
proportional representation through ranked voting in multi-seat
elections. It does so by allowing every voter one vote, that is
transferable to other candidates based on necessity of votes and the
preference of the voter. Thus, if a candidate in an election is voted
in (or in case of a tie), excess votes are allocated to candidates
according to the preference of the voter. STV is designed to minimize
the 'wasted votes' in an election by reallocating votes (and thus the
wishes of the voters) proportionally to their previous priority.

Please see the
[Wikipedia article on STV voting](https://en.wikipedia.org/wiki/Single_transferable_vote#Voting)
for more insight into how STV works.

For calculating result, we use Meek's Method with a quota derived from
the Droop Quota but with implementation changes such as those
proposed by New Zealand. See 
[this paper](http://svn.apache.org/repos/asf/steve/trunk/stv_background/meekm.pdf)
for details.

----

<h2 id="dh">D'Hondt (Jefferson) Voting</h2>

The D'Hondt method, also known as the Jefferson method, is a *highest
average* method for calculating proportional representation of parties
at an election.  In essence, this is done by calculating a quotient
per party for each number of seats available and finding the highest
values. The quotient is determined as `V/(s+1)` where `V` is the
number of votes received and `s` is the number of seats won. Thus, for
each party, the quotient is calculated for the number of seats
available:

#### Example result for election with 4 seats:

| Party | Votes | 1 seat | 2 seats | 3 seats | 4 seats | seats won |
|-------|-------|--------|---------|---------|---------|-----------|
| Gnomes | 25,000 | 25,000/(0+1) = <b style='color:#396;'>25,000</b> | 25,000/(1+1) = <b style='color:#396;'>12,500</b> | 25,000/(2+1) = 8,333 | 25,000/(3+1) = 6,250 | 2 |
| Elves | 15,000 | 15,000/(0+1) = <b style='color:#396;'>15,000</b> | 15,000/(1+1) = 7,500 | 15,000/(2+1) = 5,000 | 15,000/(3+1) = 3,750 | 1 |
| Dwarves | 10,000 | 10,000/(0+1) = <b style='color:#396;'>10,000</b> | 10,000/(1+1) = 5,000 | 10,000/(2+1) = 3,333 | 10,000/(3+1) = 2,500 | 1 |


For more information on the D'Hondt Method, see
[this Wikipedia article](https://en.wikipedia.org/wiki/D'Hondt_method)
