# Version 3 of Apache STeVe

## History

v1 was a set of command-line tools to run voting on a host server, with the
people ssh'ing to that server to cast votes.

v2 was a webapp and data server to run the voting process, utilizing emailed
tokens as "authentication" for those voting. A later modification used LDAP
to look up that token, so that email was not required (which also prevents
email interception of a voting token, which anybody could use).

v3 is intended (primarily) to revamp the data model and storage and the webui
framework, using more recent technologies for greater leverage.

## Data Model

v2 is the initial guide for a data model, to be used by v3.

The top-level item is an **Election**, and our design-point (in terms of scale)
is to manage hundreds of these. Each Election contains some simple metadata.

The number of **Persons** is numbered in low thousands, and is the entire union
of people who may be eligible to vote in any of the Elections. 

The **Issues** are the union of all issues across all Elections, and expected to
number in tens of thousands.

There is a mapping table that specifies which **Persons** are eligible to vote
in which **Issues**, which will likely reach low millions.

Lastly, there is the set of **Votes** which may reach many millions.

**Note**: these are initial scaling estimates, and the underlying SQLite database
should easily scale to these levels and beyond.

### Vote Monitors

v2 had the notion of a "Vote Monitor" which will not be used in v3. There are
no known items to monitor.

The owner/creator of an Election will be given a dashboard to view progress,
in an anonymized form.


## Hashes and Anonymity

The recorded Votes must be as anonymized as possible. The goal is to
detach Persons from their recorded Votes on Issues in a given Election. 
The data "at rest" cannot be decrypted without significant work.

It is presumed that the "root" users of the team operating the software would be
able to unmask Persons and view their votes.

Cryptographic hashes, techniques, and ciphers are used to create anonymity.

## Integrity

When an Election is "opened for voting", all metadata, Persons, and Issues,
are used to construct a singular hash (`opened_key`) that identifies
the precise state of
the Election. This hash is used to prevent any post-opening tampering of the
Election, the Persons of record, or the ballot.

The recorded votes use the `opened_key` to produce an anonymized token
for each Person and each Issue, and it is used as part of the vote encryption
process. Any attempt to alter the election will produce a new `opened_key`
value, implying that any recorded vote becomes entirely useless (the vote
can not be matched to a Person, to an Issue, nor decrypted).

## Data at Rest

(for details, see **Implementation** below)

The recorded votes are encrypted when at rest in the SQLite database. Each
vote is recorded using a token (`vote_token`) genearated as a hash of the
Person that performed the vote and the issue voted upon. Thus, a cursory
examination of the recorded votes will not
reveal people's name, nor the issues voted upon.

To reveal the votes for computing a final tally of an Issue, the
`vote_token` will be reconstructed for each voter, and used to query
the corresponding votes for the tally (only most-recent vote used).

The votes will be decrypted and fed into the issue's tally
function (based on the vote type (eg. yes/no/abstain, or Single
Transferable Vote).

When a Person loads their ballot, and needs to know which issues have
not (yet) been voted upon, then we compute a `vote_token` for each
eligible Issue, then look into the **Votes** table for rows.
The actual vote does
not need to be decrypted for this process.

## Implementation

Some notes on implementation, hashing, storage, at-rest encryption, etc.

```
ElectionID := 40 bits, as 10 hex characters
PersonID := availid from iclas.txt  # for ASF usage
IssueID := 40 bits, as 10 hex characters

ElectionData := Tuple[ ElectionID, Title ]
IssueData := Tuple[ IssueID, Title, Description, VoteType, VoteOptions ]
PersonData := Tuple[ PersonID, Email ]
BLOCK := ElectionData + sorted(IssueData) + sorted(PersonData)
OpenedKey := Hash(BLOCK, Salt(each-election))

pair = Tuple[ PersonID, IssueID ]
votestring = TBD, based on vote type

VoteToken = Hash(OpenedKey + PersonID + IssueID, Salt(each-pair))
VoteKey := PBKDF(VoteToken, Salt(each-pair))
Vote := Tuple[ VoteToken, Encrypt(VoteKey, votestring) ]
```

`ElectionID` and `IssueID` are generated 10-character hex values, using
`secrets.token_hex(5)` for cryptographic-level entropy. The 10 characters
is chosen because these values are visible in URLs and should not be too
confusing for humans. At 40 bits, the chance for collision is over a
million generated values. When generating a new ID, if a collision
actually occurs, then a new ID will be generated and tried.

When an **Election** is Opened for voting, the `OpenedKey` is calculated, stored,
and used for further work. The `OpenedKey` is primarily used to resist tampering
with the ballot definition, and to salt hash of later operations.

The `Hash()` function is **Argon2**[^argon2], producing 32 bytes.
Note that `Hash()` is
computationally/memory intensive, in order to make "unmasking" of votes
somewhat costly for **root**. Yet it needs to be reasonable to decrypt
the votestrings for final tallying (eg. after ballot-close, **several hours**
to decrypt all the votes and perform the tally).

The `Salt()` function is `secrets.token_bytes(16)` to produce 16 bytes of
cryptographic-level entropy, suitable for use by the Argon2 hash functions.
The salt values should never be transmitted.

`Encrypt()` and `Decrypt()` are a **symmetric** encryption algorithm,
so that votestrings can be recovered. This will
be implemented using the `Fernet` system[^fernet] in the `cryptography` Python
package. Note that Argon2 produces 32 byte hash values, which matches
the 32 bytes needed for a Fernet key.

### Storage and Transmission

**IMPORTANT**: the `VoteToken` should never be
stored in a way that ties them to the PersonID and IssueID.  The
`VoteKey` should never be stored. Instead, the `Salt()` values
are stored, and the token and key are computed when needed.

In general, the expense of the `Hash()` function should not be short-circuited
by storing the result. Any attacker must perform the work. During normal
operation of the voting system, each call of the `Hash()` function should be
within human-reasonable time limits (but unreasonable to perform in bulk).

Note that `VoteToken` is stored as part of each `Vote`,
but that token provides no mapping back to a Person or Issue.

The `ElectionID` and `IssueID` are visible to users, and will be encoded
as hex digits to make them relatively human-consumable.

### Entropy

There is high-entropy in the following values: `ElectionID`, `UserID`,
`VoteToken`, the two salts, and the computed (never-stored) `VoteKey`.

The `PersonID` is considered low-entropy, as it is likely a username.

Low-entropy implies a threat vector, where an attacker could use various
techniques to try "all values". However, it is combined into the
`VoteToken` with the 40-bit high-entropy `IssueID`, the 256-bit
high-entropy OpenedKey, and a 128-bit high-entropy salt value.

The `VoteKey` is a key-stretched `VoteToken` and also considered as
high-entropy and infeasible to crack.

### (Re)Tally Process

Querying the set of Issues for those associated with an ElectionID is
straight-forward.

To tally a specific issue:

1. For each Person eligible to vote on this issue, compute a `VoteToken`
2. Find the **most-recent** vote using the `VoteToken`
3. Decrypt the ciphertext to produce the original `votestring`
4. Feed these votes into the tally mechanism for the Issue's vote type.


## API Documentation

This is _TBD_

A basic example of using the API is available via the
[code coverage testing script](test/check_coverage.py).


## Threat Model

There are two primary threat vectors that can compromise the cryptographic
records of elections, people, issues, and their votes:

1. **root** on the system
2. Remote Code Execution (RCE) that can surface necessary rows from the database



[^fernet]: https://cryptography.io/en/latest/fernet/
[^argon2]: https://passlib.readthedocs.io/en/stable/lib/passlib.hash.argon2.html
