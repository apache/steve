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

        # Cursors for running queries.
        self.q_metadata = self.db.add_query('metadata',
            'SELECT * FROM METADATA')
        self.q_issues = self.db.add_query('issues',
            'SELECT * FROM ISSUES ORDER BY iid')
        self.q_record = self.db.add_query('record',
            'SELECT * FROM RECORD ORDER BY rid')

    def open(self):

        # Double-check the election is in the editing state.
        assert self.is_editable()

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

        # Simple tweak of the metadata.
        self.c_close.perform()

    def add_salts(self):
        "Set the SALT column in the ISSUES and RECORD tables."

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

    def is_tampered(self):

        # The election should be open.
        md = self.q_metadata.first_row()
        assert md.salt is not None and md.opened_key is not None

        # Compute an opened_key based on the current data.
        edata = self.gather_election_data()
        opened_key = crypto.gen_opened_key(edata, md.salt)

        print('EDATA:', edata)
        print('SALT:', md.salt)
        print('KEY:', opened_key)

        # The computed key should be unchanged.
        return opened_key != md.opened_key

    def is_editable(self):
        "Can this election be edited?"
        md = self.q_metadata.first_row()
        return md.salt is None and md.opened_key is None

    def is_open(self):
        "Is this election open for voting?"
        md = self.q_metadata.first_row()
        return (md.salt is not None
                and md.opened_key is not None
                and md.closed in (None, 0))

    def is_closed(self):
        "Has this election been closed?"
        md = self.q_metadata.first_row()
        return (md.salt is None
                and md.opened_key is None
                and md.closed == 1)


def new_eid():
    "Create a new ElectionID."

    # Use 4 bytes of a salt, for 32 bits.
    b = crypto.gen_salt()[:4]

    # Format into 8 hex characters.
    return f'{b[0]:02x}{b[1]:02x}{b[2]:02x}{b[3]:02x}'
