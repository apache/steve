# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
import json
import sqlite3
import pathlib
from contextlib import contextmanager, closing

import asfpy.db
from easydict import EasyDict as edict

from . import crypto
from . import vtypes
from .persondb import PersonNotFound

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
QUERIES = THIS_DIR.parent / 'queries.yaml'


class Election:
    # Current state of an election.
    S_EDITABLE = 'editable'
    S_OPEN = 'open'
    S_CLOSED = 'closed'

    @staticmethod
    def open_database(db_fname):
        db = asfpy.db.DB(db_fname, yaml_fname=QUERIES, yaml_section='election')
        db.conn.execute('PRAGMA foreign_keys = ON')
        return db

    def __init__(self, db_fname, eid, op='Opening', *, db=None):
        _LOGGER.debug(f'{op} election ID "{eid}"')

        self._owns_db = db is None
        self.db = self.open_database(db_fname) if db is None else db
        self.eid = eid

        try:
            if not_found(self.q_check_election, eid):
                raise ElectionNotFound(eid)
        except Exception:
            self.close_database()
            raise

    def close_database(self):
        """Close an owned connection; leave a borrowed connection to its caller."""
        if self._owns_db and self.db is not None:
            self.db.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close_database()

    @contextmanager
    def transaction(self):
        """Keep an operation atomic, including inside a caller-owned transaction."""
        conn = self.db.conn
        if conn.in_transaction:
            conn.execute('SAVEPOINT election_operation')
            try:
                yield
            except BaseException:
                if conn.in_transaction:
                    conn.execute('ROLLBACK TO SAVEPOINT election_operation')
                    conn.execute('RELEASE SAVEPOINT election_operation')
                raise
            else:
                conn.execute('RELEASE SAVEPOINT election_operation')
        else:
            with conn:
                conn.execute('BEGIN IMMEDIATE')
                yield

    def __getattr__(self, name):
        "Proxy the cursors."
        return self.__dict__.get(name, getattr(self.db, name))

    def delete(self):
        "Delete this Election and its Issues and Person/Issue pairs."

        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            self.c_delete_mayvote.perform(self.eid)
            self.c_delete_issues.perform(self.eid)
            self.c_delete_election.perform(self.eid)
        if not self.db.conn.in_transaction:
            self.close_database()

    def open(self, pdb):
        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            self.add_salts()
            edata = self.gather_election_data(pdb)
            salt = crypto.gen_salt()
            opened_key = crypto.gen_opened_key(edata, salt)
            self.c_open.perform(salt, opened_key, self.eid)

    def gather_election_data(self, pdb):
        "Gather a definition of this election for keying and anti-tamper."

        # NOTE: separators and other zero-entropy constant chars are
        # not included when assembling the data for hashing. This data
        # is not intended for human consumption, anyways.

        # NOTE: all assembly of rows must use a repeatable ordering.

        md = self._all_metadata()
        mdata = md.eid + md.title

        self.q_issues.perform(self.eid)
        # Use an f-string to render "None" if a column is NULL.
        # Render KV in its original TEXT column form. Parsing it to JSON,
        # then serializing might introduce ordering issues in any dicts.
        # This must be repeatable, so mis-ordering would be drastic.
        idata = ''.join(
            f'{i.iid}{i.title}{i.description}{i.type}{i.kv}'
            for i in self.q_issues.fetchall()
        )

        # Include the PID and EMAIL for each Person who may vote in this Election.
        # Use q_voting_persons to get distinct, sorted PIDs and emails from mayvote/issue/person join.
        self.q_voting_persons.perform(self.eid)
        pdata = ''.join(row.pid + row.email for row in self.q_voting_persons.fetchall())

        return (mdata + idata + pdata).encode()

    def close(self):
        "Close an election."

        with self.transaction():
            self._all_metadata(self.S_OPEN)
            self.c_close.perform(self.eid)

    def add_salts(self):
        "Set the SALT column in the MAYVOTE table."

        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            self.q_all_issues.perform(self.eid)
            for mayvote in self.q_all_issues.fetchall():
                self.c_salt_mayvote.perform(crypto.gen_salt(), mayvote.rowid)

    def _all_metadata(self, required_state=None):
        "INTERNAL ONLY: return all metadata about this Election."

        # NOTE: this returns the SALT and OPENED_KEY columns. This
        # API is not for public use.
        md = self.q_metadata.first_row(self.eid)
        if not md:
            raise ElectionNotFound(self.eid)

        if required_state:
            state = self._compute_state(md)
            if state != required_state:
                raise ElectionBadState(self.eid, state, required_state)

        return md

    def get_metadata(self):
        "Return basic metadata about this Election."

        md = self._all_metadata()
        # NOTE: do not return the SALT or OPENED_KEY

        return edict(
            eid=md.eid,
            title=md.title,
            owner_pid=md.owner_pid,
            authz=md.authz,
            closed=md.closed,  ### should we process this?
            open_at=md.open_at,  ### should we process this?
            close_at=md.close_at,  ### should we process this?
            state=self._compute_state(md),
        )

    def get_issue(self, iid):
        "Return TITLE, DESCRIPTION, TYPE, and KV for issue IID."

        issue = self.q_get_issue.first_row(iid)
        if not issue or issue.eid != self.eid:
            raise IssueNotFound(iid)

        return (issue.title, issue.description, issue.type, self.json2kv(issue.kv))

    def add_issue(self, title, description, vtype, kv):
        "Add a new issue with a generated unique IID."
        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            vtypes.vtype_module(vtype)
            if vtype == 'stv':
                vtypes.stv.validate_configuration(kv)

            while True:
                iid = crypto.create_id()
                try:
                    # Pure INSERT - SALT will be NULL until election opens
                    self.c_add_issue.perform(
                        iid, self.eid, title, description, vtype, self.kv2json(kv)
                    )
                    break
                except sqlite3.IntegrityError:
                    if self.q_get_issue.first_row(iid) is None:
                        raise
                    _LOGGER.debug('IID conflict ... trying again.')

            _LOGGER.info(f'Created issue[I:{iid}] in election[E:{self.eid}]')

            return iid

    def edit_issue(self, iid, title, description, vtype, kv):
        "Edit an existing issue designated by IID."
        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            self.get_issue(iid)
            vtypes.vtype_module(vtype)
            if vtype == 'stv':
                vtypes.stv.validate_configuration(kv)

            self.c_edit_issue.perform(title, description, vtype, self.kv2json(kv), iid)

            # If the issue didn't exist, we updated nothing.
            if self.c_edit_issue.rowcount == 0:
                raise IssueNotFound(iid)

            _LOGGER.info(f'Updated issue[I:{iid}] in election[E:{self.eid}]')

    def delete_issue(self, iid):
        "Delete the Issue designated by IID."

        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            self.get_issue(iid)
            self.db.conn.execute('DELETE FROM mayvote WHERE iid = ?', (iid,))
            self.c_delete_issue.perform(iid)

    def list_issues(self):
        "Return ordered EasyDict<IID, TITLE, DESCRIPTION, TYPE, KV> for all issues."

        def extract_issue(row):
            return edict(
                iid=row.iid,
                title=row.title,
                description=row.description,
                vtype=row.type,
                kv=self.json2kv(row.kv),
            )

        self.q_issues.perform(self.eid)
        return [extract_issue(row) for row in self.q_issues.fetchall()]

    def add_voter(self, pid: str, iid: str | None = None) -> None:
        "Add PID (Person) to Issue IID, or to all Issues (None)."
        with self.transaction():
            # This is only allowed while the Election is editable.
            self._all_metadata(self.S_EDITABLE)

            if iid:
                self.get_issue(iid)
                self.c_add_mayvote.perform(pid, iid)
            else:
                self.c_add_mayvote_all.perform(pid, self.eid)

    def list_voters(self):
        """List this election's eligible people without disclosing participation."""
        self.q_voters.perform(self.eid)
        return list(self.q_voters.fetchall())

    def get_voter_issues(self, pid: str) -> set[str]:
        """Return eligible issue IDs, or raise VoterNotFound for a nonmember."""
        self.q_find_issues.perform(pid, self.eid)
        iids = {row.iid for row in self.q_find_issues.fetchall()}
        if not iids:
            raise VoterNotFound(pid)
        return iids

    def add_voters(self, pids: list[str], iids: list[str]) -> None:
        """Atomically grant existing people access to selected current issues.

        Existing grants are preserved. Future issues never inherit these grants.
        """
        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            if not pids or not iids:
                raise ValueError('Select at least one voter and one issue')
            pids = list(dict.fromkeys(pids))
            iids = list(dict.fromkeys(iids))
            for iid in iids:
                self.get_issue(iid)
            for pid in pids:
                if (
                    self.db.conn.execute(
                        'SELECT 1 FROM person WHERE pid = ?', (pid,)
                    ).fetchone()
                    is None
                ):
                    raise PersonNotFound(pid)
            self.db.conn.executemany(
                'INSERT INTO mayvote (pid, iid) VALUES (?, ?) '
                'ON CONFLICT (pid, iid) DO NOTHING',
                ((pid, iid) for pid in pids for iid in iids),
            )

    def set_voter_issues(self, pid: str, iids: list[str]) -> None:
        """Replace one voter's eligibility; an empty selection removes the voter."""
        with self.transaction():
            self._all_metadata(self.S_EDITABLE)
            current = self.get_voter_issues(pid)
            selected = set(iids)
            for iid in selected:
                self.get_issue(iid)
            self.db.conn.executemany(
                'DELETE FROM mayvote WHERE pid = ? AND iid = ?',
                ((pid, iid) for iid in current - selected),
            )
            self.db.conn.executemany(
                'INSERT INTO mayvote (pid, iid) VALUES (?, ?)',
                ((pid, iid) for iid in selected - current),
            )

    def validate_vote(self, pid: str, iid: str, votestring: str):
        """Validate eligibility and ballot syntax without recording a vote."""
        if not isinstance(votestring, str):
            raise ValueError('Vote must be a string')
        self._all_metadata(self.S_OPEN)
        _, _, vtype, kv = self.get_issue(iid)
        mayvote = self.q_get_mayvote.first_row(pid, iid)
        if mayvote is None:
            raise PermissionError('Not eligible to vote on this issue')
        vtypes.vtype_module(vtype).validate_vote(votestring, kv)

    def add_vote(self, pid: str, iid: str, votestring: str):
        "Add VOTESTRING as the (latest) vote by PID for IID."
        self.add_votes(pid, {iid: votestring})

    def add_votes(self, pid: str, votes: dict[str, str]):
        """Record a ballot atomically, rejecting it entirely if any issue is invalid."""
        with self.transaction():
            for iid, votestring in votes.items():
                self.validate_vote(pid, iid, votestring)
            for iid, votestring in votes.items():
                self._record_vote(pid, iid, votestring)

    def _record_vote(self, pid, iid, votestring):
        md = self._all_metadata(self.S_OPEN)
        mayvote = self.q_get_mayvote.first_row(pid, iid)
        vote_token = crypto.gen_vote_token(md.opened_key, pid, iid, mayvote.salt)

        # Pass MAYVOTE.SALT for PBKDF.
        ciphertext = crypto.create_vote(vote_token, mayvote.salt, votestring)

        self.c_add_vote.perform(vote_token, ciphertext)

    def tally_issue(self, iid):
        """Return the results for a given ISSUE-ID.

        This is a 2-tuple: a human-readable string, and vtype-specific
        supporting data.

        Note: it is expected the caller has other details associated
        with the issue, and knows the vote type and how to interpret
        the supporting data.
        """

        # The Election should be closed.
        md = self._all_metadata(self.S_CLOSED)

        ### TBD: we need a param to "spy" on Open elections
        # md = self._all_metadata()

        # Need the issue TYPE
        self.get_issue(iid)
        issue = self.q_get_issue.first_row(iid)

        # Accumulate PID values for each person who voted on IID.
        voters = set()

        # Accumulate all MOST-RECENT votes for Issue IID.
        votes = []

        # Use mayvote to determine all eligible voters for Issue IID.
        self.q_tally.perform(iid)
        for mayvote in self.q_tally.fetchall():
            # Each row is: PID, IID, SALT

            # For the given Person PID found, compute a VOTE_TOKEN.
            vote_token = crypto.gen_vote_token(
                md.opened_key,
                mayvote.pid,
                iid,
                mayvote.salt,
            )

            # We don't need/want all columns, so only pick CIPHERTEXT.
            row = self.q_recent_vote.first_row(vote_token)

            # This PID may not have voted on IID.
            if row is None:
                continue

            # There is a vote by this PID. Record the voter.
            voters.add(mayvote.pid)

            # Get the original votestring using the token/salt.
            votestring = crypto.decrypt_votestring(
                vote_token,
                mayvote.salt,
                row.ciphertext,
            )
            votes.append(votestring)

        # Make sure the votes are NOT in database-order.
        # Note: we are not returning the votes, so this may be
        #  superfluous. But it certainly should not hurt.
        crypto.shuffle(votes)  # in-place

        # Perform the tally, and return the results and voters.
        m = vtypes.vtype_module(issue.type)
        return m.tally(votes, self.json2kv(issue.kv)), voters

    def has_voted_upon(self, pid):
        "Return {ISSUE-ID: BOOL} stating what has been voted upon."

        # The Election should be open.
        md = self._all_metadata(self.S_OPEN)

        voted_upon = {}

        self.q_find_issues.perform(pid, self.eid)
        for row in self.q_find_issues.fetchall():
            # Query is mayvote.* ... so ROW is: PID, IID, SALT
            vote_token = crypto.gen_vote_token(
                md.opened_key,
                pid,
                row.iid,
                row.salt,
            )

            # Is any vote present? (wicked fast)
            voted = self.q_has_voted.first_row(vote_token)

            voted_upon[row.iid] = voted is not None

        return voted_upon

    def is_tampered(self, pdb):
        # The Election should be open (don't allow voting when TAMPERED)
        # or it may be closed (don't bother tallying, if TAMPERED).
        #
        # ... if in the editable state, then the OPENED_KEY check below will
        #     simply fail. So don't call when in that state. Your fault.
        md = self._all_metadata()  # no required state

        # Compute an opened_key based on the current data.
        edata = self.gather_election_data(pdb)
        opened_key = crypto.gen_opened_key(edata, md.salt)

        # The computed key should be unchanged.
        return opened_key != md.opened_key

    def is_editable(self):
        "Can this Election be edited?"
        return self.get_state() == self.S_EDITABLE

    def is_open(self):
        "Is this Election open for voting?"
        return self.get_state() == self.S_OPEN

    def is_closed(self):
        "Has this Election been closed?"
        return self.get_state() == self.S_CLOSED

    def get_state(self):
        "Derive our election state from the METADATA table."

        return self._compute_state(self._all_metadata())

    @classmethod
    def _compute_state(cls, md):
        "Compute Election state, given all metadata."

        if md.closed == 1:
            assert md.salt is not None and md.opened_key is not None
            return cls.S_CLOSED
        assert md.closed in (None, 0)

        if md.salt is None:
            assert md.opened_key is None
            return cls.S_EDITABLE
        assert md.opened_key is not None

        return cls.S_OPEN

    @staticmethod
    def kv2json(kv):
        "Convert a structured KV into a JSON string for storage."
        # Note: avoid serializing None.
        return kv and json.dumps(kv)

    @staticmethod
    def json2kv(j):
        "Convert the KV JSON string back into its structured value."
        return j and json.loads(j)

    @classmethod
    def create(
        cls,
        db_fname,
        title,
        owner_pid,
        authz=None,
        open_at=None,
        close_at=None,
        *,
        db=None,
    ):
        """Create an election, optionally in a caller-owned database transaction."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError('Election title is required')
        owns_db = db is None
        if owns_db:
            db = cls.open_database(db_fname)
        try:
            while True:
                eid = crypto.create_id()
                try:
                    db.c_create.perform(eid, title, owner_pid, authz, open_at, close_at)
                    break
                except sqlite3.IntegrityError:
                    if not_found(db.q_check_election, eid):
                        raise
                    _LOGGER.debug('EID conflict ... trying again.')
            election = cls(db_fname, eid, op='Opening NEW', db=db)
            election._owns_db = owns_db
            return election
        except Exception:
            if owns_db:
                db.conn.close()
            raise

    @classmethod
    def delete_by_eid(cls, db_fname, eid):
        "Delete the specified Election."
        with cls(db_fname, eid) as election:
            election.delete()

    @classmethod
    def open_to_pid(cls, db_fname, pid):
        "List of elections are OPEN for PID to vote upon."

        db = cls.open_database(db_fname)

        # Run the generator to get all rows. Returned as EasyDicts.
        with closing(db.conn):
            db.q_open_to_me.perform(pid)
            return list(db.q_open_to_me.fetchall())

    @classmethod
    def owned_elections(cls, db_fname, pid):
        "List of elections are that PID has created."

        db = cls.open_database(db_fname)

        # NOTE: contains subset of columns. We don't want to return the
        #       SALT or OPENED_KEY values.
        #
        # Run the generator to get all rows. Returned as EasyDicts.
        with closing(db.conn):
            db.q_owned.perform(pid)
            return list(db.q_owned.fetchall())

    @classmethod
    def upcoming_to_pid(cls, db_fname, pid):
        "List of editable elections for PID to vote upon."

        db = cls.open_database(db_fname)

        # Run the generator to get all rows. Returned as EasyDicts.
        with closing(db.conn):
            db.q_upcoming_to_me.perform(pid)
            return list(db.q_upcoming_to_me.fetchall())

    @classmethod
    def list_closed_election_ids(cls, db_fname, include_open=False):
        "Return a list of Election IDs for closed elections, optionally including open ones."
        db = cls.open_database(db_fname)

        with closing(db.conn):
            db.q_closed_election_ids.perform()
            eids = [row.eid for row in db.q_closed_election_ids.fetchall()]
            if include_open:
                db.q_open_election_ids.perform()
                eids.extend(row.eid for row in db.q_open_election_ids.fetchall())
            return eids

    def set_open_at(self, timestamp):
        "Set the open_at timestamp for this Election."
        self.c_set_open_at.perform(timestamp, self.eid)

    def set_close_at(self, timestamp):
        "Set the close_at timestamp for this Election."
        self.c_set_close_at.perform(timestamp, self.eid)

    def get_voters_for_email(self):
        "Return a list of distinct voters (pid, name, email) eligible for this election."
        self.q_voting_persons.perform(self.eid)
        return [
            edict(pid=row.pid, name=row.name, email=row.email)
            for row in self.q_voting_persons.fetchall()
        ]


def not_found(cursor, key):
    row = cursor.first_row(key)
    return row is None


class ElectionNotFound(Exception):
    def __init__(self, eid):
        self.eid = eid
        super().__init__(str(self))

    def __str__(self):
        return f'Election[E:{self.eid}] not found'


class ElectionBadState(Exception):
    def __init__(self, eid, current, required):
        self.eid = eid
        self.current = current
        self.required = required
        super().__init__(str(self))

    def __str__(self):
        return (
            f'Election[E:{self.eid}]'
            f' is "{self.current}" but should be "{self.required}"'
        )


class IssueNotFound(Exception):
    def __init__(self, iid):
        self.iid = iid
        super().__init__(str(self))

    def __str__(self):
        return f'Issue[I:{self.iid}] not found'


class VoterNotFound(Exception):
    def __init__(self, pid):
        self.pid = pid
        super().__init__(f'Voter[P:{pid}] not found in this election')
