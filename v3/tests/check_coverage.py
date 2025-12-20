#!/usr/bin/env python3

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

import sys
import os
import sqlite3
import logging
import pathlib

import coverage

# Ensure that we can import the "steve" package.
THIS_DIR = pathlib.Path(__file__).resolve().parent
PARENT_DIR = THIS_DIR.parent

TESTING_DB = THIS_DIR / 'covtest.db'
SCHEMA_FILE = PARENT_DIR / 'schema.sql'


def touch_every_line():
    "A minimal test to run each line in the 'steve' package."

    # Do the imports *WITHIN* the coverage test.
    import steve.election
    import steve.persondb

    # Start the election, and open it.
    try:
        os.remove(TESTING_DB)
    except OSError:
        pass
    conn = sqlite3.connect(TESTING_DB, isolation_level=None)
    conn.executescript(open(SCHEMA_FILE).read())
    conn.close()

    # Ready to load up the Election and exercise it.
    e = steve.election.Election.create(TESTING_DB, 'coverage', 'alice')

    _ = e.get_metadata()  # while EDITABLE

    pdb = steve.persondb.PersonDB(TESTING_DB)
    pdb.add_person('alice', 'Alice', 'alice@example.org')
    pdb.add_person('bob', None, 'bob@example.org')
    pdb.add_person('carlos', 'Carlos', 'carlos@example.org')
    pdb.add_person('david', None, 'david@example.org')
    _ = pdb.list_persons()
    pdb.delete_person('david')
    _ = pdb.get_person('alice')

    i1 = e.add_issue('issue A', None, 'yna', None)
    i2 = e.add_issue(
        'issue B',
        None,
        'stv',
        {
            'seats': 3,
            'labelmap': {
                'a': 'Alice',
                'b': 'Bob',
                'c': 'Carlos',
                'd': 'David',
                'e': 'Eve',
            },
        },
    )
    _ = e.list_issues()
    i3 = e.add_issue('issue C', None, 'yna', None)
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

    # Complete coverage: delete an election.
    e2 = steve.election.Election.create(TESTING_DB, 'E2', 'alice')
    # Provide some data that should get deleted.
    ### note: the referential integrity should to into a test suite.
    _ = e2.add_issue('issue E2.A', None, 'yna', None)
    e2.add_voter('alice')
    e2.delete()

    # Use the class method this time.
    eid = steve.election.Election.create(TESTING_DB, 'E3', 'alice').eid
    steve.election.Election.delete_by_eid(TESTING_DB, eid)


def main():
    cov = coverage.Coverage(
        data_file=None,
        branch=True,
        config_file=False,
        source_pkgs=['steve'],
        messages=True,
    )
    cov.start()

    try:
        touch_every_line()
    finally:
        cov.stop()

    cov.report(file=sys.stdout)
    cov.html_report(directory=str(THIS_DIR / 'covreport'))


if __name__ == '__main__':
    DATE_FORMAT = '%m/%d %H:%M'
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='[{asctime}|{levelname}|{module}] {message}',
        datefmt=DATE_FORMAT,
    )
    main()
