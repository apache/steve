# Version 3 of Apache STeVe

## History

v1 was a set of command-line tools to run voting on a host server, with the
people ssh'ing to that server to cast votes.

v2 was a webapp and data server to run the voting process, utilizing LDAP
authentication for the people voting.

v3 is intended (primarily) to revamp the data model/storage and the webui
frameworks, using more recent technologies for greater leverage.

## Data Model

v2 is the initial guide for a data model, to be used by v3.

The top-level item is an **Election**, and our design-point (in terms of scale)
is to manage hundreds of these.

Each **Election** contains some simple metadata, along with **Persons**
(numbering in the hundreds) that are on record to vote, a set of **Issues**
(also, hundreds) on the ballot for the people to vote upon, and a small
set of **Vote Monitors** (single digit count) for the Election.

This will produce a set of **Votes** (tens of thousands).

### Vote Monitors (and Attacks?)

This role is undefined.

Once an election is opened, no changes to the ballot are allowed, so the
Monitors cannot affect an election. With read-only status, what should they
be looking for?

* Alice voting as Bob (see below)
* Alice stuffing ballots (eg. as a person not on Record; should be impossible)

Each person receives a **token** to represent themself during voting. The
token is regarded as a **shared secret** between STeVe and the Person.

Note: this token could be used internally, and the **shared secret** would be
the Person's LDAP password. This *may* create undesired data in access logs,
which could be solved by custom config to **omit** the authenticated user from
the logs. And/or, a Person could sign in to retrieve a link that embeds
their token, and that link requires no authentication (note: would need to
ensure that **all** browsers obey path-based directives on when to send
credentials; we'd only want creds for retrieving the token/link, but for them
to be dropped during voting the ballot).

Given the above, if Alice is able to discover Bob's token, then she can vote
as if she were Bob. This may be discoverable by aberrant repeat voting by Bob.

Since votes may only be performed by those on record, with person tokens, it
does not seem possible for Alice to stuff the ballot box.

?? other attack vectors? can Monitors help with any?

## Hashes and Anonymity

The Persons must be as anonymous as possible. The goal is that Persons
and Monitors cannot "unmask" any Person in the election, nor the Votes that
they have cast.

It is presumed that the "root" users of the team operating the software would be
able to unmask Persons and view their votes.

Cryptographic-grade hashes are used as identifiers to create anonymity.

## Integrity

When an Election is "opened for voting", all Persons, Issues, and Monitors
will be used to construct a singular hash (`opened_key`) that identifies
the precise state of
the Election. This hash is used to prevent any post-opening tampering of the
Persons of record, the ballot, or those watching for such tampering.

The recorded votes use the `opened_key` to produce the anonymized tokens
for each Person and each Issue, and it is used as part of the vote encryption
process. Any attempt to alter the election will produce a new `opened_key`
value, implying that any recorded vote becomes entirely useless (the vote
can not be matched to a Person, to an Issue, nor decrypted).

## Data at Rest

(for details, see **Implementation** below)

The recorded votes are encrypted when at rest in the SQLite database. Each
vote is recorded using a hashed form of the Person that performed the vote
(`person_token`), and a hashed version of the issue voted upon
(`issue_token`). Thus, a cursory examination of the recorded votes will not
reveal people's name, nor the issues voted upon.

To reveal the votes for computing a final tally, the `person_token` will
be used in its opaque form -- there is no need to pair these tokens to
visible names. For a given issue, its `issue_token` is computed and
all rows with that token are selected. If two or more selected rows have
the same `person_token` (a Person filed a later vote), then only the
most-recent row is used in the tally process. Each vote is decrypted
using the `person_token` and the `issue_token` from that row, along
with a unique per-vote salt value. The decrypted vote is then tallied
according to the chosen vote type (eg. yes/no/abstain, or Single
Transferable Vote).

When a Person loads their ballot, and needs to know which issues have
not (yet) been voted upon, then we compute the `person_token` for them.
For each issue on the ballot, we compute the `issue_token` and see if
the votes contain any rows with those two tokens. The actual vote does
not need to be decrypted for this process.

Note that to reveal each recorded vote requires one (1) expensive hash
computation, and one (1) expensive decryption. Additional hash
computations are required to pair each Person and each Issue with
their corresponding tokens. These operations are all salted to increase
the entropy.

## Implementation

Some notes on implementation, hashing, storage, at-rest encryption, etc.

```
ElectionID := 32 bits
PersonID := availid from iclas.txt  # for ASF usage
IssueID := [-a-zA-Z0-9]+

ElectionData := Tuple[ ElectionID, Title ]
IssueData := Tuple[ IssueID, Title, Description, VoteType, VoteOptions ]
PersonData := Tuple[ PersonID, Name, Email ]
BLOCK := ElectionData + sorted(IssueData) + sorted(PersonData)
OpenedKey := Hash(BLOCK, Salt(each-election))

Persons := Map<PersonID, Salt(each-person)>
PersonToken := Hash(OpenedKey + PersonID, Salt(each-person))

Issues := Map<IssueID, Salt(each-issue)>
IssueToken := Hash(OpenedKey + IssueID, Salt(each-issue))

votestring = TBD; padding TBD
VoteKey := Hash(PersonToken + IssueToken, Salt(each-vote))
Vote := Tuple[ PersonToken, IssueToken, Salt(each-vote), Encrypt(VoteKey, votestring) ]
```

When an **Election** is Opened for voting, the `OpenedKey` is calculated, stored,
and used for further work. The `OpenedKey` is primarily used to resist tampering
with the ballot definition.

The size of **Salt(xx)** is 16 bytes, which is the default used by the Argon2
implementation. The salt values should never be transmitted.

The `Hash()` function will be **Argon2**[^argon2]. Note that `Hash()` is
computationally/memory intensive, in order to make "unmasking" of votes
somewhat costly for **root**. Yet it needs to be reasonable to decrypt
the votestrings for final tallying (eg. after ballot-close, **several hours**
to decrypt all the votes and perform the tally).

`Encrypt()` and `Decrypt()` are a **symmetric** encryption algorithm,
so that votestrings can be recovered. This will
be implemented using the `Fernet` system[^fernet] in the `cryptography` Python
package. Note that Argon2 produces 32 byte hash values, which matches
the 32 bytes needed for a Fernet key.

### Storage and Transmission

**IMPORTANT**: the `PersonToken` and `IssueToken` should never be
stored in a way that ties them to the PersonID and IssueID.  The
`VoteKey` should never be stored. Instead, the `Salt(xx)` values
are stored, and the tokens/key are computed when needed.

In general, the expense of the `Hash()` function should not be short-circuited
by storing the result. Any attacker must perform the work. During normal
operation of the voting system, each call of the `Hash()` function should be
within human-reasonable time limits (but unreasonable to perform in bulk).

Note that `PersonToken` and `IssueToken` are stored as part of each `Vote`,
but those tokens provide no easy mapping back to a person or issue.

The `PersonToken` is normally emailed to the Person. If it is not
emailed, then LDAP authentication would be used, and the server will
compute it from the authenticated credentials.

Since `PersonToken` *may* be used by the Person, via URL, to perform
their voting, it must be "URL safe". If LDAP authn mode is used, then
the `PersonToken` will never be encoded for humans.

The `ElectionID` is also visible to Persons, and will be encoded
as eight (8) hex digits, just like STeVe v2.

### (Re)Tally Process

  1. For each issue on the ballot, the `IssueToken` is computed and
     entered into a `Map<IssueToken, IssueID>`
  1. For each vote in the election:
     1. Compute the `VoteKey`
     1. Decrypt the `votestring`
     1. Look up the `IssueID`, and apply `votestring` to that issue

Notes: be wary of repeats; collect STV votestrings, for passing in-bulk
to the STV algorithm.

Note that the tally process does not require unmasking the Person.

### API Documentation

This is _TBD_

A basic example of using the API is available via the
[code coverage testing script](test/check_coverage.py).


[^fernet]: https://cryptography.io/en/latest/fernet/
[^argon2]: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.argon2.html
