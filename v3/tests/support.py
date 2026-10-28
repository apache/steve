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

import pathlib
import sqlite3
import tempfile
import unittest

from steve.election import Election
from steve.persondb import PersonDB

ROOT = pathlib.Path(__file__).resolve().parents[1]


class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='steve-test-')
        self.addCleanup(directory.cleanup)
        self.db_path = pathlib.Path(directory.name) / 'steve.db'
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript((ROOT / 'schema.sql').read_text())
        conn.close()
        self.pdb = PersonDB.open(self.db_path)
        self.addCleanup(self.pdb.db.conn.close)
        for pid in ('alice', 'bob', 'carlos', 'iroh', 'wells'):
            self.pdb.add_person(pid, pid.title(), f'{pid}@example.org')

    def create_election(self, owner='alice'):
        election = Election.create(self.db_path, 'Test election', owner)
        self.addCleanup(election.close_database)
        return election

    def add_stv_issue(self, election):
        return election.add_issue(
            'Choose a candidate',
            '',
            'stv',
            {
                'version': 2,
                'seats': 1,
                'labelmap': {'a': ['alice', 'Alice'], 'b': ['bob', 'Bob']},
            },
        )
