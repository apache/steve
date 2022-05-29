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

    def open(self):
        pass

    def close(self):
        pass

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
