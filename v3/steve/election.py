#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ----
#
# ### TBD: DOCCO
#
#

import logging
import json
import sqlite3

from . import crypto
from . import db
from . import vtypes

_LOGGER = logging.getLogger(__name__)


class Election:

    # Current state of an election.
    S_EDITABLE = 'editable'
    S_OPEN = 'open'
    S_CLOSED = 'closed'

    def __init__(self, db_fname, eid):
        _LOGGER.debug(f'Opening election ID "{eid}"')

        ### switch to asfpy.db
        self.db = db.DB(db_fname)
        self.eid = eid

        # Construct cursors for all operations.
        self.c_salt_mayvote = self.db.add_statement(
            'UPDATE mayvote SET salt = ? WHERE _ROWID_ = ?')
        self.c_open = self.db.add_statement(
            'UPDATE ELECTIONS SET salt = ?, opened_key = ?'
            ' WHERE eid = ?')
        self.c_close = self.db.add_statement(
            'UPDATE ELECTIONS SET closed = 1'
            ' WHERE eid = ?')
        self.c_add_issue = self.db.add_statement(
            '''INSERT INTO ISSUES VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT DO UPDATE SET
                 title=excluded.title,
                 description=excluded.description,
                 type=excluded.type,
                 kv=excluded.kv
            ''')
        self.c_delete_issue = self.db.add_statement(
            'DELETE FROM ISSUES WHERE iid = ?')
        self.c_add_vote = self.db.add_statement(
            'INSERT INTO VOTES VALUES (NULL, ?, ?)')
        self.c_add_mayvote = self.db.add_statement(
            'INSERT INTO mayvote (pid, iid, salt) VALUES (?, ?, NULL)')
        self.c_add_mayvote_all = self.db.add_statement(
            'INSERT INTO mayvote (pid, iid, salt)'
            ' SELECT ?, iid, NULL FROM issues WHERE eid = ?')
        self.c_delete_mayvote = self.db.add_statement(
            '''DELETE FROM mayvote
               WHERE iid IN (
                 SELECT iid
                 FROM issues
                 WHERE eid = ?
               )''')
        self.c_delete_issues = self.db.add_statement(
            'DELETE FROM issues WHERE eid = ?')
        self.c_delete_election = self.db.add_statement(
            'DELETE FROM elections WHERE eid = ?')

        # Cursors for running queries.
        self.q_metadata = self.db.add_query('elections',
            'SELECT * FROM ELECTIONS WHERE eid = ?')
        self.q_issues = self.db.add_query('issues',
            'SELECT * FROM ISSUES WHERE eid = ? ORDER BY iid')
        self.q_get_issue = self.db.add_query('issues',
            'SELECT * FROM ISSUES WHERE iid = ?')
        self.q_get_mayvote = self.db.add_query('mayvote',
            'SELECT * FROM MAYVOTE WHERE pid = ? AND iid = ?')
        self.q_tally = self.db.add_query('mayvote',
            'SELECT * FROM MAYVOTE WHERE iid = ?')

        # Manual queries: these queries do not follow the 'SELECT * '
        # pattern, so we cannot use .add_query() and will not have
        # attribute access to the row results while running the query.
        self.m_find_issues = self.db.add_statement(
            '''SELECT m.*
               FROM mayvote m
               JOIN issues i ON m.iid = i.iid
               WHERE m.pid = ? AND i.eid = ?
            ''')
        self.m_has_voted = self.db.add_statement(
            '''SELECT 1 FROM VOTES
               WHERE vote_token = ?
               LIMIT 1
            ''')
        self.m_recent_vote = self.db.add_statement(
            '''SELECT ciphertext FROM VOTES
               WHERE vote_token = ?
               ORDER BY _ROWID_ DESC
               LIMIT 1
            ''')
        self.m_all_issues = self.db.add_statement(
            '''SELECT m._ROWID_
               FROM mayvote m
               JOIN issues i ON m.iid = i.iid
               WHERE i.eid = ?;
            ''')

    def delete(self):
        "Delete this Election and its Issues and Person/Issue pairs."

        # Can't delete if it has been opened (even if later closed).
        assert self.is_editable()

        self.db.conn.execute('BEGIN TRANSACTION')

        # Order these things because of referential integrity.

        # Delete all rows that refer to Issues within this Election.
        self.c_delete_mayvote.perform((self.eid,))

        # Now, delete all the Issues that are part of this Election.
        self.c_delete_issues.perform((self.eid,))

        # Finally, remove the Election itself.
        self.c_delete_election.perform((self.eid,))

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
        self.c_open.perform((salt, opened_key, self.eid))

    def gather_election_data(self, pdb):
        "Gather a definition of this election for keying and anti-tamper."

        # NOTE: separators and other zero-entropy constant chars are
        # not included when assembling the data for hashing. This data
        # is not intended for human consumption, anyways.

        # NOTE: all assembly of rows must use a repeatable ordering.

        md = self.q_metadata.first_row((self.eid,))
        mdata = md.eid + md.title

        self.q_issues.perform((self.eid,))
        # Use an f-string to render "None" if a column is NULL.
        idata = ''.join(f'{i.iid}{i.title}{i.description}{i.type}{i.kv}'
                        for i in self.q_issues.fetchall())

        ### we don't want all people. Just those who are allowed to
        ### vote in this Election. Examine the "mayvote" table.
        ### list_persons returns 3-tuples of (PID,NAME,EMAIL). We only
        ### want pid/email in PDATA.
        pdata = ''.join(p[0] + p[2] for p in pdb.list_persons())

        return (mdata + idata + pdata).encode()

    def close(self):
        "Close an election."

        # The Election should be open.
        assert self.is_open()

        # Simple tweak of the metadata to close the Election.
        self.c_close.perform((self.eid,))

    def add_salts(self):
        "Set the SALT column in the MAYVOTE table."

        # The Election should be editable.
        assert self.is_editable()

        # Use M_ALL_ISSUES to iterate over all Person/Issue mappings
        # in this Election (specified by EID).
        self.db.conn.execute('BEGIN TRANSACTION')
        self.m_all_issues.perform((self.eid,))
        for mayvote in self.m_all_issues.fetchall():
            # MAYVOTE is a 1-tuple: _ROWID_

            # Use a distinct cursor to insert the SALT value.
            salt = crypto.gen_salt()
            self.c_salt_mayvote.perform((salt, mayvote[0]))

        self.db.conn.execute('COMMIT')

    def get_metadata(self):
        "Return basic metadata about this Election."

        md = self.q_metadata.first_row((self.eid,))
        # NOTE: do not return the SALT
        # note: likely: never return opened_key

        return md.eid, md.title, self.get_state()

    def get_issue(self, iid):
        "Return TITLE, DESCRIPTION, TYPE, and KV for issue IID."

        # NEVER return issue.salt
        issue = self.q_get_issue.first_row((iid,))

        return (issue.title, issue.description, issue.type,
                self.json2kv(issue.kv))

    def add_issue(self, iid, title, description, vtype, kv):
        "Add or update an issue designated by IID."
        assert self.is_editable()
        assert vtype in vtypes.TYPES

        # If we ADD, then SALT will be NULL. If we UPDATE, then it will not
        # be touched (it should be NULL).
        self.c_add_issue.perform((iid, self.eid, title, description, vtype,
                                  self.kv2json(kv)))

    def delete_issue(self, iid):
        "Delete the Issue designated by IID."

        # Can only delete Issues before the Election is OPEN.
        assert self.is_editable()

        self.c_delete_issue.perform((iid,))

    def list_issues(self):
        "Return ordered (IID, TITLE, DESCRIPTION, TYPE, KV) for all ISSUES."

        def extract_issue(row):
            # NOTE: the SALT column is omitted. It should never be exposed.
            return row[:4] + (self.json2kv(row.kv),)

        self.q_issues.perform((self.eid,))
        return [ extract_issue(row) for row in self.q_issues.fetchall() ]

    def add_voter(self, pid: str, iid: str | None = None) -> None:
        "Add PID (Person) to Issue IID, or to all Issues (None)."

        # This is only allowed while the Election is editable.
        assert self.is_editable()

        if iid:
            self.c_add_mayvote.perform((pid, iid,))
        else:
            self.c_add_mayvote_all.perform((pid, self.eid,))

    def add_vote(self, pid: str, iid: str, votestring: str):
        "Add VOTESTRING as the (latest) vote by PID for IID."

        # The Election should be open.
        assert self.is_open()

        md = self.q_metadata.first_row((self.eid,))

        ### validate VOTESTRING for ISSUE.TYPE voting

        mayvote = self.q_get_mayvote.first_row((pid, iid,))
        vote_token = crypto.gen_vote_token(md.opened_key, pid, iid, mayvote.salt)

        # Pass MAYVOTE.SALT for PBKDF.
        ciphertext = crypto.create_vote(vote_token, mayvote.salt, votestring)

        self.c_add_vote.perform((vote_token, ciphertext))

    def tally_issue(self, iid):
        """Return the results for a given ISSUE-ID.

        This is a 2-tuple: a human-readable string, and vtype-specific
        supporting data.

        Note: it is expected the caller has other details associated
        with the issue, and knows the vote type and how to interpret
        the supporting data.
        """

        # The Election should be closed.
        assert self.is_closed()

        md = self.q_metadata.first_row((self.eid,))

        # Need the issue TYPE
        issue = self.q_get_issue.first_row((iid,))

        # Accumulate all MOST-RECENT votes for Issue IID.
        votes = [ ]

        # Use mayvote to determine all potential voters for Issue IID.
        self.q_tally.perform((iid,))
        for mayvote in self.q_tally.fetchall():
            # Each row is: PID, IID, SALT

            # For the given Person PID found, compute a VOTE_TOKEN.
            vote_token = crypto.gen_vote_token(
                md.opened_key, mayvote.pid, iid, mayvote.salt,
            )

            # We don't need/want all columns, so only pick CIPHERTEXT.
            row = self.m_recent_vote.first_row((vote_token,))
            votestring = crypto.decrypt_votestring(
                vote_token, mayvote.salt, row[0],
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
        assert self.is_open()

        md = self.q_metadata.first_row((self.eid,))

        voted_upon = { }

        self.m_find_issues.perform((pid, self.eid,))
        for row in self.m_find_issues.fetchall():
            # Query is mayvote.* ... so ROW is: PID, IID, SALT
            vote_token = crypto.gen_vote_token(
                md.opened_key, pid, row[1], row[2]
            )

            # Is any vote present? (wicked fast)
            voted = self.m_has_voted.first_row((vote_token,))

            voted_upon[row[1]] = (voted is not None)

        return voted_upon

    def is_tampered(self, pdb):

        # The Election should be open.
        assert self.is_open()

        md = self.q_metadata.first_row((self.eid,))

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

        md = self.q_metadata.first_row((self.eid,))
        if md.closed == 1:
            assert md.salt is not None and md.opened_key is not None
            return self.S_CLOSED
        assert md.closed in (None, 0)

        if md.salt is None:
            assert md.opened_key is None
            return self.S_EDITABLE
        assert md.opened_key is not None

        return self.S_OPEN

    @staticmethod
    def kv2json(kv):
        'Convert a structured KV into a JSON string for storage.'
        # Note: avoid serializing None.
        return kv and json.dumps(kv)

    @staticmethod
    def json2kv(j):
        'Convert the KV JSON string back into its structured value.'
        return j and json.loads(j)

    @classmethod
    def create(cls, db_fname, title, owner_pid, authz=None):
        # Open in autocommit
        conn = sqlite3.connect(db_fname, isolation_level=None)
        while True:
            eid = crypto.create_id()
            try:
                conn.execute('INSERT INTO elections (eid, title, owner_pid)'
                             ' VALUES (?, ?, ?)',
                             (eid, title, owner_pid,))
                break
            except sqlite3.IntegrityError:
                _LOGGER.debug('EID conflict(!!) ... trying again.')
        conn.close()

        return cls(db_fname, eid)

    @classmethod
    def delete_by_eid(cls, db_fname, eid):
        "Delete the specified Election."
        cls(db_fname, eid).delete()
