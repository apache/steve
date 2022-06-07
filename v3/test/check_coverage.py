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
import json

import coverage

# Ensure that we can import the "steve" package.
THIS_DIR = os.path.realpath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(THIS_DIR)
sys.path.insert(0, PARENT_DIR)

TESTING_DB = os.path.join(THIS_DIR, 'covtest.db')
SCHEMA_FILE = os.path.join(PARENT_DIR, 'schema.sql')


def touch_every_line():
    "A minimal test to run each line in the 'steve' package."

    # Do the import *WITHIN* the coverage test.
    import steve.election

    eid = steve.election.new_eid()

    # Start the election, and open it.
    try:
        os.remove(TESTING_DB)
    except OSError:
        pass
    conn = sqlite3.connect(TESTING_DB)
    conn.executescript(open(SCHEMA_FILE).read())
    conn.execute('INSERT INTO METADATA'
                 f' VALUES ("{eid}", "title", NULL, NULL, NULL)')
    conn.commit()

    # Ready to load up the Election and exercise it.
    e = steve.election.Election(TESTING_DB)

    _ = e.get_metadata()  # while EDITABLE

    e.add_person('alice', 'Alice', 'alice@example.org')
    e.add_person('bob', None, 'bob@example.org')
    e.add_person('carlos', 'Carlos', 'carlos@example.org')
    e.add_person('david', None, 'david@example.org')
    _ = e.list_persons()
    e.delete_person('david')
    _ = e.get_person('alice')

    e.add_issue('a', 'issue A', None, 'yna', None)
    e.add_issue('b', 'issue B', None, 'stv', {
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
    e.add_issue('c', 'issue C', None, 'yna', None)
    e.delete_issue('c')
    _ = e.get_issue('a')

    e.open()
    _ = e.get_metadata()  # while OPEN
    e.add_vote('alice', 'a', 'y')
    e.add_vote('bob', 'a', 'n')
    e.add_vote('carlos', 'a', 'a')  # use each of Y/N/A
    e.add_vote('alice', 'b', 'bc')
    e.add_vote('bob', 'b', 'ad')
    _ = e.has_voted_upon('alice')
    _ = e.is_tampered()

    e.close()
    _ = e.get_metadata()  # while CLOSED
    _ = e.tally_issue('a')
    _ = e.tally_issue('b')


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
