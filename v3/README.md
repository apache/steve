# Version 3 of Apache STeVe

## History

v1 was a set of command-line tools to run voting on a host server, with the
participants ssh'ing to that server to cast votes.

v2 was a webapp and data server to run the voting process, utilizing LDAP
authentication for the participants.

v3 is intended (primarily) to revamp the data model/storage and the webui
frameworks, using more recent technologies for greater leverage.

## Data Model

v2 is the initial guide for a data model, to be used by v3.

The top-level item is an **Election**, and our design-point (in terms of scale)
is to manage hundreds of these.

Each **Election** contains some simple metadata, along with **Participants**
(numbering in the hundreds) that are on record to vote, a set of **Issues**
(also, hundreds) on the ballot for the participants to vote upon, and a small
set of **Vote Monitors** (single digit count) for the Election.

This will produce a set of **Votes** (tens of thousands).

### Vote Monitors (and Attacks?)

This role is undefined.

Once an election is opened, no changes to the ballot are allowed, so the
Monitors cannot affect an election. With read-only status, what should they
be looking for?

* Alice voting as Bob (see below)
* Alice stuffing ballots (eg. as a person not on Record; should be impossible)

Each participant receives a **token** to represent themself during voting. The
token is regarded as a **shared secret** between STeVe and the Participant.

Note: this token could be used internally, and the **shared secret** would be
the Participant's LDAP password. This *may* create undesired data in access logs,
which could be solved by custom config to **omit** the authenticated user from
the logs. And/or, a Participant could sign in to retrieve a link that embeds
their token, and that link requires no authentication (note: would need to
ensure that **all** browsers obey path-based directives on when to send
credentials; we'd only want creds for retrieving the token/link, but for them
to be dropped during voting the ballot).

Given the above, if Alice is able to discover Bob's token, then she can vote
as if she were Bob. This may be discoverable by aberrant repeat voting by Bob.

Since votes may only be performed by those on record, with voter tokens, it
does not seem possible for Alice to stuff the ballot box.

?? other attack vectors? can Monitors help with any?

## Hashes and Anonymity

The participants must be as anonymous as possible. The goal is that Participants
and Monitors cannot "unmask" any Participant in the election, nor the Votes that
they have cast.

It is presumed that the "root" users of the team operating the software would be
able to unmask Participants and view their votes.

Cryptographic-grade hashes are used as identifiers to create anonymity.

## Integrity

When an Election is "opened for voting", all Participants, Issues, and Monitors
will be used to construct a singular hash that identifies the precise state of
the Election. This hash is used to prevent any post-opening tampering of the
voters of record, the ballot, or those watching for such tampering.

## Implementation

Some notes on implementation, hashing, storage, at-rest encryption, etc.

```
ElectionID := 32 bits
VoterID := availid from iclas.txt
IssueID := [-a-zA-Z0-9]+

Election-data := TBD
Issue-data := TBD
BLOCK := Election-data + sorted(Issue-Data)
OpenedKey := Hash(BLOCK)

Voters := Map<VoterID, Salt(each-voter)>
VoterToken := Hash(OpenedKey + VoterID + Salt(each-voter))

Issues := Map<IssueID, Salt(each-issue)>
IssueToken := Hash(OpenedKey + IssueID + Salt(each-issue))

VoteKey := Hash(VoterToken + IssueToken + Salt(each-vote))
Vote := Tuple[ VoterToken, IssueToken, Salt(each-vote), Encrypt(VoteKey, votestring) ]
```

When an **Election** is Opened for voting, the `OpenedKey` is calculated, stored,
and used for further work. The `OpenedKey` is primarily used to resist tampering
with the ballot definition.

The size of **Salt(xx)** is 16 bytes, which is the default used by the Argon2
implementation. The salt values should never be transmitted.

The `Hash()` function will be **Argon2**. Note that `Hash()` is
computationally/memory intensive, in order to make "unmasking" of votes
somewhat costly for **root**. Yet it needs to be reasonable to decrypt
the votestrings for final tallying (eg. after ballot-close, **several hours**
to decrypt all the votes and perform the tally).

`Encrypt()` and `Decrypt()` are a **symmetric** encryption algorithm
(eg. block-based XOR), so that votestrings can be recovered. TBD.

**IMPORTANT**: the `IssueToken` and `VoteKey` should never be stored.
In general, the expense of the `Hash()` function should not be short-circuited
by storing the result. Any attacker must perform the work. During normal
operation of the voting system, each call of the `Hash()` function should be
within human-reasonable time limits (but unreasonable to perform in bulk).

Note that `VoteToken` is stored as part of each vote, but is only emailed
as the shared secret. It is not stored outside of votes, and is not
obviously tied in any way to VoterID.

If `VoteToken` is not emailed, but (instead) LDAP authentication is used,
then it is possible to omit storage of `VoteToken` and to simply compute it
from the authenticated credentials.

### (Re)Tally Process

  1. For each issue on the ballot, the `IssueToken` is computed and
     entered into a `Map<IssueToken, IssueID>`
  1. For each vote in the election:
     1. Compute the `VoteKey`
     1. Decrypt the `votestring`
     1. Look up the IssueID, and apply votestring to that issue

Notes: be wary of repeats; collect STV votestrings, for passing in-bulk
to the STV algorithm.
