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

from . import crypto
from . import db


class Election:

    def __init__(self, eid, db_fname):
        self.eid = eid
        self.db = db.DB(db_fname)

        # Construct cursors for all operations.
        self.c_salt_issue = self.db.add_statement(
            '''UPDATE ISSUES SET salt = ? WHERE _ROWID_ = ?''')
        self.c_salt_record = self.db.add_statement(
            '''UPDATE RECORD SET salt = ? WHERE _ROWID_ = ?''')
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
        self.c_add_record = self.db.add_statement(
            '''INSERT INTO RECORD VALUES (?, ?, ?, ?)
               ON CONFLICT DO UPDATE SET
                 name=excluded.name,
                 email=excluded.email
            ''')
        self.c_delete_issue = self.db.add_statement(
            'DELETE FROM ISSUES WHERE iid = ?')
        self.c_delete_record = self.db.add_statement(
            'DELETE FROM RECORD WHERE rid = ?')

        # Cursors for running queries.
        self.q_metadata = self.db.add_query('metadata',
            'SELECT * FROM METADATA')
        self.q_issues = self.db.add_query('issues',
            'SELECT * FROM ISSUES ORDER BY iid')
        self.q_record = self.db.add_query('record',
            'SELECT * FROM RECORD ORDER BY rid')
        self.q_get_issue = self.db.add_query('issues',
            'SELECT * FROM ISSUES WHERE iid = ?')
        self.q_get_record = self.db.add_query('record',
            'SELECT * FROM RECORD WHERE rid = ?')

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
        idata = ''.join(f'{r.iid}{r.title}{r.description}{r.type}{r.kv}'
                        for r in self.q_issues.fetchall())

        self.q_record.perform()
        rdata = ''.join(r.rid + r.email
                        for r in self.q_record.fetchall())

        return (mdata + idata + rdata).encode()

    def close(self):
        "Close an election."

        # The Election should be open.
        assert self.is_open()

        # Simple tweak of the metadata to close the Election.
        self.c_close.perform()

    def add_salts(self):
        "Set the SALT column in the ISSUES and RECORD tables."

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
        for_table('record', self.c_salt_record)

    def get_issue(self, iid):
        "Return TITLE, DESCRIPTION, TYPE, and KV for issue IID."

        # NEVER return issue.salt
        issue = self.q_get_issue.first_row((iid,))
        return issue.title, issue.description, issue.type, issue.kv

    def add_issue(self, iid, title, description, type, kv):
        "Add or update an issue designated by IID."
        assert self.is_editable()

        # If we ADD, then SALT will be NULL. If we UPDATE, then it will not
        # be touched (it should be NULL).
        self.c_add_issue.perform((iid, title, description, type, kv, None))

    def delete_issue(self, iid):
        "Delete the Issue designated by IID."
        assert self.is_editable()

        self.c_delete_issue.perform((iid,))

    def get_participant(self, rid):
        "Return NAME, EMAIL for Participant on record RID."

        # NEVER return record.salt
        record = self.q_get_record.first_row((rid,))
        return record.name, record.email

    def add_participant(self, rid, name, email):
        "Add or update a Participant (voter of record) designated by RID."
        assert self.is_editable()

        # If we ADD, then SALT will be NULL. If we UPDATE, then it will not
        # be touched (it should be NULL).
        self.c_add_record.perform((rid, name, email, None))

    def delete_participant(self, rid):
        "Delete the Participant designated by RID."
        assert self.is_editable()

        self.c_delete_record.perform((rid,))

    def is_tampered(self):

        # The Election should be open.
        assert self.is_opened()

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
        md = self.q_metadata.first_row()
        return md.salt is None and md.opened_key is None

    def is_open(self):
        "Is this Election open for voting?"
        md = self.q_metadata.first_row()
        return (md.salt is not None
                and md.opened_key is not None
                and md.closed in (None, 0))

    def is_closed(self):
        "Has this Election been closed?"
        md = self.q_metadata.first_row()
        return (md.salt is None
                and md.opened_key is None
                and md.closed == 1)


def new_eid():
    "Create a new ElectionID."

    # Use 4 bytes of a salt, for 32 bits.
    b = crypto.gen_salt()

    # Format into 8 hex characters.
    return f'{b[0]:02x}{b[1]:02x}{b[2]:02x}{b[3]:02x}'
