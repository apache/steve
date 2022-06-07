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

import sys
import json

from . import crypto
from . import db
from . import vtypes


class Election:

    # Current state of an election.
    S_EDITABLE = 'editable'
    S_OPEN = 'open'
    S_CLOSED = 'closed'

    def __init__(self, db_fname):
        self.db = db.DB(db_fname)

        # Construct cursors for all operations.
        self.c_salt_issue = self.db.add_statement(
            'UPDATE ISSUES SET salt = ? WHERE _ROWID_ = ?')
        self.c_salt_person = self.db.add_statement(
            'UPDATE PERSON SET salt = ? WHERE _ROWID_ = ?')
        self.c_open = self.db.add_statement(
            'UPDATE METADATA SET salt = ?, opened_key = ?')
        self.c_close = self.db.add_statement(
            'UPDATE METADATA SET closed = 1')
        self.c_add_issue = self.db.add_statement(
            '''INSERT INTO ISSUES VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT DO UPDATE SET
                 title=excluded.title,
                 description=excluded.description,
                 type=excluded.type,
                 kv=excluded.kv
            ''')
        self.c_add_person = self.db.add_statement(
            '''INSERT INTO PERSON VALUES (?, ?, ?, ?)
               ON CONFLICT DO UPDATE SET
                 name=excluded.name,
                 email=excluded.email
            ''')
        self.c_delete_issue = self.db.add_statement(
            'DELETE FROM ISSUES WHERE iid = ?')
        self.c_delete_person = self.db.add_statement(
            'DELETE FROM PERSON WHERE pid = ?')
        self.c_add_vote = self.db.add_statement(
            'INSERT INTO VOTES VALUES (NULL, ?, ?, ?, ?)')
        self.c_has_voted = self.db.add_statement(
            '''SELECT 1 FROM VOTES
               WHERE person_token = ? AND issue_token = ?
               LIMIT 1
            ''')

        # Cursors for running queries.
        self.q_metadata = self.db.add_query('metadata',
            'SELECT * FROM METADATA')
        self.q_issues = self.db.add_query('issues',
            'SELECT * FROM ISSUES ORDER BY iid')
        self.q_person = self.db.add_query('person',
            'SELECT * FROM PERSON ORDER BY pid')
        self.q_get_issue = self.db.add_query('issues',
            'SELECT * FROM ISSUES WHERE iid = ?')
        self.q_get_person = self.db.add_query('person',
            'SELECT * FROM PERSON WHERE pid = ?')
        self.q_by_issue = self.db.add_query('votes',
            'SELECT * FROM VOTES WHERE issue_token = ? ORDER BY _ROWID_')

    def open(self):

        # Double-check the Election is in the editing state.
        assert self.is_editable()

        # Add salts first. If this is gonna fail, then make sure it
        # happens before we move to the "opened" state.
        self.add_salts()

        edata = self.gather_election_data()
        print('EDATA:', edata)
        salt = crypto.gen_salt()
        opened_key = crypto.gen_opened_key(edata, salt)

        print('SALT:', salt)
        print('KEY:', opened_key)
        self.c_open.perform((salt, opened_key))

    def gather_election_data(self):
        "Gather a definition of this election for keying and anti-tamper."

        # NOTE: separators and other zero-entropy constant chars are
        # not included when assembling the data for hashing. This data
        # is not intended for human consumption, anyways.

        # NOTE: all assembly of rows must use a repeatable ordering.

        md = self.q_metadata.first_row()
        mdata = md.eid + md.title

        self.q_issues.perform()
        # Use an f-string to render "None" if a column is NULL.
        idata = ''.join(f'{i.iid}{i.title}{i.description}{i.type}{i.kv}'
                        for i in self.q_issues.fetchall())

        self.q_person.perform()
        pdata = ''.join(p.pid + p.email
                        for p in self.q_person.fetchall())

        return (mdata + idata + pdata).encode()

    def close(self):
        "Close an election."

        # The Election should be open.
        assert self.is_open()

        # Simple tweak of the metadata to close the Election.
        self.c_close.perform()

    def add_salts(self):
        "Set the SALT column in the ISSUES and PERSON tables."

        # The Election should be editable.
        assert self.is_editable()

        cur = self.db.conn.cursor()

        def for_table(table, mod_cursor):
            "Use MOD_CURSOR to salt each row of TABLE."

            # Fetch all ROWID values now, to avoid two cursors
            # attempting to work on TABLE at the same time.
            cur.execute(f'SELECT _ROWID_ FROM {table}')
            ids = cur.fetchall()

            # Now, add a salt to every row.
            for r in ids:
                salt = crypto.gen_salt()
                print('ROW will use:', table, r[0], salt)
                mod_cursor.perform((salt, r[0]))

        for_table('issues', self.c_salt_issue)
        for_table('person', self.c_salt_person)

    def get_metadata(self):
        "Return basic metadata about this Election."

        md = self.q_metadata.first_row()
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
        self.c_add_issue.perform((iid, title, description, vtype,
                                  self.kv2json(kv), None))

    def delete_issue(self, iid):
        "Delete the Issue designated by IID."
        assert self.is_editable()

        self.c_delete_issue.perform((iid,))

    def list_issues(self):
        "Return ordered (IID, TITLE, DESCRIPTION, TYPE, KV) for all ISSUES."

        def extract_issue(row):
            # NOTE: the SALT column is omitted. It should never be exposed.
            return row[:4] + (self.json2kv(row.kv),)

        self.q_issues.perform()
        return [ extract_issue(row) for row in self.q_issues.fetchall() ]

    def get_person(self, pid):
        "Return NAME, EMAIL for Person identified by PID."

        # NEVER return person.salt
        person = self.q_get_person.first_row((pid,))
        return person.name, person.email

    def add_person(self, pid, name, email):
        "Add or update a Person designated by PID."
        assert self.is_editable()

        # If we ADD, then SALT will be NULL. If we UPDATE, then it will not
        # be touched (it should be NULL).
        self.c_add_person.perform((pid, name, email, None))

    def delete_person(self, pid):
        "Delete the Person designated by PID."
        assert self.is_editable()

        self.c_delete_person.perform((pid,))

    def list_persons(self):
        "Return ordered (PID, NAME, EMAIL) for each Person."

        # NOTE: the SALT column is omitted. It should never be exposed.
        self.q_person.perform()
        return [ row[:3] for row in self.q_person.fetchall() ]

    def add_vote(self, pid, iid, votestring):
        "Add VOTESTRING as the (latest) vote by PID for IID."

        # The Election should be open.
        assert self.is_open()

        md = self.q_metadata.first_row()
        person = self.q_get_person.first_row((pid,))
        issue = self.q_get_issue.first_row((iid,))

        ### validate VOTESTRING for ISSUE.TYPE voting

        person_token = crypto.gen_token(md.opened_key, pid, person.salt)
        #print('PERSON:', pid, person.salt, person_token)
        issue_token = crypto.gen_token(md.opened_key, iid, issue.salt)
        #print('ISSUE:', iid, issue.salt, issue_token)

        salt, token = crypto.create_vote(person_token, issue_token, votestring)
        #print('SALT:', salt)
        #print('TOKEN:', token)
        self.c_add_vote.perform((person_token, issue_token, salt, token))

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

        md = self.q_metadata.first_row()
        issue = self.q_get_issue.first_row((iid,))
        issue_token = crypto.gen_token(md.opened_key, iid, issue.salt)

        # Use this dict to retain "most recent" votes.
        dedup = { }  # (PERSON_TOKEN, ISSUE_TOKEN) : VOTESTRING

        self.q_by_issue.perform((issue_token,))
        for row in self.q_by_issue.fetchall():
            votestring = crypto.decrypt_votestring(
                row.person_token, issue_token, row.salt, row.token)
            dedup[row.person_token, row.issue_token] = votestring

        # Make sure the votes are not in database-order.
        # Note: we are not returning the votes, so this may be
        #  superfluous. But it certainly should not hurt.
        votes = list(dedup.values())
        crypto.shuffle(votes)  # in-place

        # Perform the tally, and return the results.
        m = vtypes.vtype_module(issue.type)
        return m.tally(votes, self.json2kv(issue.kv))

    def has_voted_upon(self, pid):
        "Return {ISSUE-ID: BOOL} stating what has been voted upon."

        # The Election should be open.
        assert self.is_open()

        md = self.q_metadata.first_row()
        person = self.q_get_person.first_row((pid,))
        person_token = crypto.gen_token(md.opened_key, pid, person.salt)

        voted_upon = { }

        self.q_issues.perform()
        for issue in self.q_issues.fetchall():
            issue_token = crypto.gen_token(md.opened_key,
                                           issue.iid,
                                           issue.salt)

            # Is any vote present?
            self.c_has_voted.perform((person_token, issue_token))
            row = self.c_has_voted.fetchone()
            _ = self.c_has_voted.fetchall()  # should be empty (LIMIT 1)

            #print('HAS-VOTED:', row, '||', person_token, issue_token)
            voted_upon[issue.iid] = row is not None

        return voted_upon

    def is_tampered(self):

        # The Election should be open.
        assert self.is_open()

        md = self.q_metadata.first_row()

        # Compute an opened_key based on the current data.
        edata = self.gather_election_data()
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

        md = self.q_metadata.first_row()
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


def new_eid():
    "Create a new ElectionID."

    # Use 4 bytes of a salt, for 32 bits.
    b = crypto.gen_salt()

    # Format into 8 hex characters.
    return f'{b[0]:02x}{b[1]:02x}{b[2]:02x}{b[3]:02x}'
