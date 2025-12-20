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

import asfpy.db
import easydict

from . import crypto
from . import vtypes

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
        return asfpy.db.DB(db_fname, yaml_fname=QUERIES, yaml_section='election')

    def __init__(self, db_fname, eid, op='Opening'):
        _LOGGER.debug(f'{op} election ID "{eid}"')

        self.db = self.open_database(db_fname)
        self.eid = eid

        if not_found(self.q_check_election, eid):
            raise ElectionNotFound(eid)

    def __getattr__(self, name):
        "Proxy the cursors."
        return self.__dict__.get(name, getattr(self.db, name))

    def delete(self):
        "Delete this Election and its Issues and Person/Issue pairs."

        # Can't delete if it has been opened (even if later closed).
        assert self.is_editable()

        # Normally, we are in auto-commit mode. Switch to transactional.
        self.db.conn.execute('BEGIN TRANSACTION')

        # Order these things because of referential integrity.

        # Delete all rows that refer to Issues within this Election.
        self.c_delete_mayvote.perform(self.eid)

        # Now, delete all the Issues that are part of this Election.
        self.c_delete_issues.perform(self.eid)

        # Finally, remove the Election itself.
        self.c_delete_election.perform(self.eid)

        self.db.conn.execute('COMMIT')

        # Disable this instance.
        self.db.conn.close()
        self.db = None

    def open(self, pdb):
        # Double-check the Election is in the editing state.
        assert self.is_editable()

        # Add salts first. If this is gonna fail, then make sure it
        # happens before we move to the "opened" state.
        self.add_salts()

        edata = self.gather_election_data(pdb)
        print('EDATA:', edata)
        salt = crypto.gen_salt()
        opened_key = crypto.gen_opened_key(edata, salt)

        print('SALT:', salt)
        print('KEY:', opened_key)
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
        idata = ''.join(
            f'{i.iid}{i.title}{i.description}{i.type}{i.kv}'
            for i in self.q_issues.fetchall()
        )

        # Include the PID and EMAIL for each Person.
        ### we don't want all people. Just those who are allowed to
        ### vote in this Election. Examine the "mayvote" table.
        pdata = ''.join(p.pid + p.email for p in pdb.list_persons())

        return (mdata + idata + pdata).encode()

    def close(self):
        "Close an election."

        # The Election should be open.
        assert self.is_open()

        # Simple tweak of the metadata to close the Election.
        self.c_close.perform(self.eid)

    def add_salts(self):
        "Set the SALT column in the MAYVOTE table."

        # The Election should be editable.
        assert self.is_editable()

        # Use Q_ALL_ISSUES to iterate over all Person/Issue mappings
        # in this Election (specified by EID).

        # Normally, we are in auto-commit mode. Switch to transactional.
        self.db.conn.execute('BEGIN TRANSACTION')

        self.q_all_issues.perform(self.eid)
        for mayvote in self.q_all_issues.fetchall():
            # MAYVOTE is a 1-tuple: _ROWID_
            # print('COLUMNS:', dir(mayvote))

            # Use a distinct cursor to insert the SALT value.
            salt = crypto.gen_salt()
            self.c_salt_mayvote.perform(salt, mayvote.rowid)

        self.db.conn.execute('COMMIT')

    def _disappeared(self):
        "The Election disappeared in the database. Disable SELF."

        # Disable this instance.
        self.db.conn.close()
        self.db = None

        # The caller may want to inform this EID no longer exists.
        return ElectionNotFound(self.eid)

    def _all_metadata(self, required_state=None):
        "INTERNAL ONLY: return all metadata about this Election."

        # NOTE: this returns the SALE and OPENED_KEY columns. This
        # API is not for public use.
        md = self.q_metadata.first_row(self.eid)
        if not md:
            raise self._disappeared()

        if required_state:
            state = self._compute_state(md)
            if state != required_state:
                raise ElectionBadState(self.eid, state, required_state)

        return md

    def get_metadata(self):
        "Return basic metadata about this Election."

        md = self._all_metadata()
        # NOTE: do not return the SALT or OPENED_KEY

        return md.eid, md.title, self._compute_state(md)

    def get_issue(self, iid):
        "Return TITLE, DESCRIPTION, TYPE, and KV for issue IID."

        issue = self.q_get_issue.first_row(iid)
        if not issue:
            raise IssueNotFound(iid)

        # NEVER return issue.salt
        return (issue.title, issue.description, issue.type, self.json2kv(issue.kv))

    def add_issue(self, title, description, vtype, kv):
        "Add a new issue with a generated unique IID."
        assert self.is_editable()
        assert vtype in vtypes.TYPES

        while True:
            iid = crypto.create_id()
            try:
                # Pure INSERT - SALT will be NULL until election opens
                self.c_add_issue.perform(
                    iid, self.eid, title, description, vtype, self.kv2json(kv)
                )
                break
            except sqlite3.IntegrityError:
                _LOGGER.debug('IID conflict(!!) ... trying again.')

        _LOGGER.info(f'Created issue[I:{iid}] in election[E:{self.eid}]')

        return iid

    def edit_issue(self, iid, title, description, vtype, kv):
        "Update an existing issue designated by IID."
        assert self.is_editable()
        assert vtype in vtypes.TYPES

        self.c_edit_issue.perform(
            title, description, vtype, self.kv2json(kv), iid
        )

        # If the issue didn't exist, we updated nothing.
        if self.c_edit_issue.rowcount == 0:
            raise IssueNotFound(iid)

        _LOGGER.info(f'Updated issue[I:{iid}] in election[E:{self.eid}]')

    def delete_issue(self, iid):
        "Delete the Issue designated by IID."

        # Can only delete Issues before the Election is OPEN.
        assert self.is_editable()

        self.c_delete_issue.perform(iid)

        # If the issue didn't exist, we deleted nothing.
        if self.c_delete_issue.rowcount == 0:
            raise IssueNotFound(iid)
        # else .rowcount == 1

    def list_issues(self):
        "Return ordered EasyDicgt<IID, TITLE, DESCRIPTION, TYPE, KV> for all ISSUES."

        def extract_issue(row):
            return easydict.EasyDict(
                iid=row.iid,
                title=row.title,
                description=row.description,
                type=row.type,
                kv=self.json2kv(row.kv),
            )

        self.q_issues.perform(self.eid)
        return [extract_issue(row) for row in self.q_issues.fetchall()]

    def add_voter(self, pid: str, iid: str | None = None) -> None:
        "Add PID (Person) to Issue IID, or to all Issues (None)."

        # This is only allowed while the Election is editable.
        assert self.is_editable()

        if iid:
            self.c_add_mayvote.perform(pid, iid)
        else:
            self.c_add_mayvote_all.perform(pid, self.eid)

    def add_vote(self, pid: str, iid: str, votestring: str):
        "Add VOTESTRING as the (latest) vote by PID for IID."

        # The Election should be open.
        md = self._all_metadata(self.S_OPEN)

        ### validate VOTESTRING for ISSUE.TYPE voting

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

        # Need the issue TYPE
        issue = self.q_get_issue.first_row(iid)

        # Accumulate all MOST-RECENT votes for Issue IID.
        votes = []

        # Use mayvote to determine all potential voters for Issue IID.
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

        # Perform the tally, and return the results.
        m = vtypes.vtype_module(issue.type)
        return m.tally(votes, self.json2kv(issue.kv))

    def has_voted_upon(self, pid):
        "Return {ISSUE-ID: BOOL} stating what has been voted upon."

        # The Election should be open.
        md = self._all_metadata(self.S_OPEN)

        voted_upon = {}

        self.q_find_issues.perform(pid, self.eid)
        for row in self.q_find_issues.fetchall():
            # print('COLUMNS:', dir(row))

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
        # The Election should be open.
        md = self._all_metadata(self.S_OPEN)

        # Compute an opened_key based on the current data.
        edata = self.gather_election_data(pdb)
        opened_key = crypto.gen_opened_key(edata, md.salt)

        print('EDATA:', edata)
        print('SALT:', md.salt)
        print('KEY:', opened_key)

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
        cls, db_fname, title, owner_pid, authz=None, open_at=None, close_at=None
    ):
        ### Open in autocommit??
        db = cls.open_database(db_fname)

        while True:
            eid = crypto.create_id()
            try:
                db.c_create.perform(eid, title, owner_pid,
                                    authz, open_at, close_at)
                break
            except sqlite3.IntegrityError:
                _LOGGER.debug('EID conflict(!!) ... trying again.')
        _LOGGER.info(f'Created election[E:{eid}]')

        return cls(db_fname, eid, op='Opening NEW')

    @classmethod
    def delete_by_eid(cls, db_fname, eid):
        "Delete the specified Election."
        cls(db_fname, eid).delete()

    @classmethod
    def open_to_pid(cls, db_fname, pid):
        "List of elections are OPEN for PID to vote upon."

        db = cls.open_database(db_fname)

        # Run the generator to get all rows. Returned as EasyDicts.
        db.q_open_to_me.perform(
            pid,
        )
        return [row for row in db.q_open_to_me.fetchall()]

    @classmethod
    def owned_elections(cls, db_fname, pid):
        "List of elections are that PID has created."

        db = cls.open_database(db_fname)

        # NOTE: contains subset of columns. We don't want to return the
        #       SALT or OPENED_KEY values.
        #
        # Run the generator to get all rows. Returned as EasyDicts.
        db.q_owned.perform(
            pid,
        )
        return [row for row in db.q_owned.fetchall()]


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
