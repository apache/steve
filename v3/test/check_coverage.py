#!/usr/bin/env python3
#
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
#
# ----
#
# ### TBD: DOCCO
#


import sys
import os.path
import sqlite3

import coverage  # pip3 install coverage

# Ensure that we can import the "steve" package.
THIS_DIR = os.path.realpath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(THIS_DIR)
sys.path.insert(0, PARENT_DIR)

TESTING_DB = os.path.join(THIS_DIR, 'covtest.db')
SCHEMA_FILE = os.path.join(PARENT_DIR, 'schema.sql')


def touch_every_line():
    "A minimal test to run each line in the 'steve' package."

    # Do the imports *WITHIN* the coverage test.
    import steve.election
    import steve.crypto
    import steve.persondb

    eid = steve.election.new_eid()

    # Start the election, and open it.
    try:
        os.remove(TESTING_DB)
    except OSError:
        pass
    conn = sqlite3.connect(TESTING_DB)
    conn.executescript(open(SCHEMA_FILE).read())
    conn.execute('INSERT INTO ELECTIONS VALUES'
                 f' ("{eid}", "title", "alice", NULL, NULL, NULL, NULL)')
    conn.commit()

    # Ready to load up the Election and exercise it.
    e = steve.election.Election(TESTING_DB, eid)

    _ = e.get_metadata()  # while EDITABLE

    pdb = steve.persondb.PersonDB(TESTING_DB)
    pdb.add_person('alice', 'Alice', 'alice@example.org')
    pdb.add_person('bob', None, 'bob@example.org')
    pdb.add_person('carlos', 'Carlos', 'carlos@example.org')
    pdb.add_person('david', None, 'david@example.org')
    _ = pdb.list_persons()
    pdb.delete_person('david')
    _ = pdb.get_person('alice')

    i1 = steve.crypto.create_id()
    i2 = steve.crypto.create_id()
    i3 = steve.crypto.create_id()

    e.add_issue(i1, eid, 'issue A', None, 'yna', None)
    e.add_issue(i2, eid, 'issue B', None, 'stv', {
        'seats': 3,
        'labelmap': {
            'a': 'Alice',
            'b': 'Bob',
            'c': 'Carlos',
            'd': 'David',
            'e': 'Eve',
            },
        })
    _ = e.list_issues()
    e.add_issue(i3, eid, 'issue C', None, 'yna', None)
    e.delete_issue(i3)
    _ = e.get_issue(i1)

    # Alice and Bob can vote on all issues. Carlos only on i1.
    e.add_voter('alice')
    e.add_voter('bob')
    e.add_voter('carlos', i1)

    e.open(pdb)
    _ = e.get_metadata()  # while OPEN
    e.add_vote('alice', i1, 'y')
    e.add_vote('bob', i1, 'n')
    e.add_vote('carlos', i1, 'a')  # use each of Y/N/A
    e.add_vote('alice', i2, 'bc')
    e.add_vote('bob', i2, 'ad')
    _ = e.has_voted_upon('alice')
    _ = e.is_tampered(pdb)

    e.close()
    _ = e.get_metadata()  # while CLOSED
    _ = e.tally_issue(i1)
    _ = e.tally_issue(i2)


def main():
    cov = coverage.Coverage(
        data_file=None, branch=True, config_file=False,
        source_pkgs=['steve'], messages=True,
        )
    cov.start()

    try:
        touch_every_line()
    finally:
        cov.stop()

    cov.report(file=sys.stdout)
    cov.html_report(directory='covreport')


if __name__ == '__main__':
    main()
