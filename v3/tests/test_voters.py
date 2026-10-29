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

import sqlite3

from steve.election import ElectionBadState, IssueNotFound, VoterNotFound
from steve.persondb import PersonNotFound
from support import DatabaseTestCase


class VoterTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.election = self.create_election()
        self.first = self.election.add_issue('First issue', '', 'yna', None)
        self.second = self.election.add_issue('Second issue', '', 'yna', None)

    def test_batch_add_preserves_existing_grants_and_deduplicates(self):
        self.election.add_voter('bob', self.first)
        self.election.add_voters(['bob', 'carlos', 'bob'], [self.second, self.second])
        self.election.add_voters(['bob', 'carlos'], [self.second])
        self.assertEqual(
            self.election.get_voter_issues('bob'), {self.first, self.second}
        )
        self.assertEqual(self.election.get_voter_issues('carlos'), {self.second})
        self.assertEqual(
            [(v.pid, v.issue_count) for v in self.election.list_voters()],
            [('bob', 2), ('carlos', 1)],
        )
        self.assertEqual(self.election.get_voters_for_email()[0].pid, 'bob')

    def test_batch_rejects_unknown_people_and_foreign_issues_without_partial_grants(
        self,
    ):
        other = self.create_election('bob')
        foreign = other.add_issue('Other election', '', 'yna', None)
        for pids, iids, error in (
            (['bob', 'missing'], [self.first], PersonNotFound),
            (['Bob'], [self.first], PersonNotFound),
            (['bob'], [self.first, foreign], IssueNotFound),
            (['bob'], [], ValueError),
            ([], [self.first], ValueError),
        ):
            with self.subTest(pids=pids, iids=iids), self.assertRaises(error):
                self.election.add_voters(pids, iids)
            self.assertEqual(self.election.list_voters(), [])

    def test_batch_database_failure_rolls_back_inside_caller_transaction(self):
        self.election.db.conn.executescript("""
            CREATE TRIGGER reject_second_grant BEFORE INSERT ON mayvote
            WHEN (SELECT COUNT(*) FROM mayvote) > 0
            BEGIN SELECT RAISE(ABORT, 'storage failure'); END;
        """)
        with self.election.transaction():
            with self.assertRaises(sqlite3.IntegrityError):
                self.election.add_voters(['bob'], [self.first, self.second])
        self.assertEqual(self.election.list_voters(), [])

    def test_replacement_and_removal_are_scoped_to_one_voter_and_election(self):
        other = self.create_election('bob')
        foreign = other.add_issue('Other election', '', 'yna', None)
        other.add_voter('bob', foreign)
        self.election.add_voters(['bob', 'carlos'], [self.first])
        with self.assertRaises(IssueNotFound):
            self.election.set_voter_issues('bob', [self.second, foreign])
        self.assertEqual(self.election.get_voter_issues('bob'), {self.first})
        self.election.set_voter_issues('bob', [self.second])
        self.assertEqual(self.election.get_voter_issues('bob'), {self.second})
        self.election.set_voter_issues('bob', [])
        with self.assertRaises(VoterNotFound):
            self.election.set_voter_issues('bob', [self.first])
        self.assertEqual(self.election.get_voter_issues('carlos'), {self.first})
        self.assertEqual(other.get_voter_issues('bob'), {foreign})
        self.assertEqual(self.pdb.get_person('bob')[0], 'Bob')

    def test_replacement_storage_failure_restores_previous_grants(self):
        self.election.add_voter('bob', self.first)
        self.election.db.conn.executescript("""
            CREATE TRIGGER reject_grant BEFORE INSERT ON mayvote
            BEGIN SELECT RAISE(ABORT, 'storage failure'); END;
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            self.election.set_voter_issues('bob', [self.second])
        self.assertEqual(self.election.get_voter_issues('bob'), {self.first})

    def test_new_issues_start_empty_and_opening_freezes_all_grants(self):
        self.election.add_voters(['bob'], [self.first, self.second])
        new = self.election.add_issue('Later issue', '', 'yna', None)
        self.assertNotIn(new, self.election.get_voter_issues('bob'))
        self.election.open(self.pdb)
        for state in ('open', 'closed'):
            if state == 'closed':
                self.election.close()
            for change in (
                lambda: self.election.add_voters(['carlos'], [new]),
                lambda: self.election.set_voter_issues('bob', [new]),
                lambda: self.election.set_voter_issues('bob', []),
            ):
                with self.subTest(state=state), self.assertRaises(ElectionBadState):
                    change()
            self.assertEqual(
                self.election.get_voter_issues('bob'), {self.first, self.second}
            )
            self.assertFalse(self.election.is_tampered(self.pdb))
