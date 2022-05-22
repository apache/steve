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
