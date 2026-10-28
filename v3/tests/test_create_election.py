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

import datetime
import importlib.util
import sqlite3
from unittest.mock import patch

import yaml

from support import DatabaseTestCase, ROOT
from steve.election import Election

spec = importlib.util.spec_from_file_location(
    'create_election', ROOT / 'server/bin/create-election.py'
)
assert spec is not None and spec.loader is not None
create_election = importlib.util.module_from_spec(spec)
spec.loader.exec_module(create_election)


class CreateElectionTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.definition = {
            'election': {'title': 'Election', 'owner_pid': 'alice'},
            'issues': [{'title': 'Approve', 'vtype': 'yna'}],
            'record': ['iroh'],
        }

    def run_import(self):
        path = self.db_path.parent / 'election.yaml'
        path.write_text(yaml.safe_dump(self.definition))
        with patch.object(create_election, 'DB_FNAME', self.db_path):
            return create_election.main(path)

    def test_import_preserves_requested_voter_identity(self):
        eid = self.run_import()
        with Election(self.db_path, eid) as election:
            self.assertEqual([v.pid for v in election.get_voters_for_email()], ['iroh'])

    def test_unknown_or_duplicate_voters_leave_no_election(self):
        for voters in (['missing'], ['bob', 'bob']):
            with self.subTest(voters=voters):
                self.definition['record'] = voters
                with self.assertRaises(ValueError):
                    self.run_import()
                self.assertEqual(Election.owned_elections(self.db_path, 'alice'), [])

    def test_storage_failure_rolls_back_election_and_issues(self):
        self.pdb.db.conn.executescript("""
            CREATE TRIGGER fail_issue BEFORE INSERT ON issue
            WHEN NEW.title = 'broken'
            BEGIN SELECT RAISE(ABORT, 'Storage failure'); END;
        """)
        self.definition['issues'].append({'title': 'broken', 'vtype': 'yna'})
        with self.assertRaises(sqlite3.IntegrityError):
            self.run_import()
        self.assertEqual(Election.owned_elections(self.db_path, 'alice'), [])
        self.assertEqual(
            self.pdb.db.conn.execute('SELECT COUNT(*) AS n FROM issue').fetchone().n, 0
        )

    def test_yaml_dates_are_utc_and_epoch_zero_is_preserved(self):
        self.assertEqual(create_election.parse_datetime(0), 0)
        self.assertEqual(create_election.parse_datetime('1970-01-01'), 0)
        self.assertEqual(create_election.parse_datetime(datetime.date(1970, 1, 1)), 0)
        self.assertEqual(create_election.parse_datetime('1970-01-01T01:00:00+01:00'), 0)
        self.definition['election']['open_at'] = datetime.date(2026, 11, 1)
        eid = self.run_import()
        with Election(self.db_path, eid) as election:
            expected = int(
                datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc).timestamp()
            )
            self.assertEqual(election.get_metadata().open_at, expected)
