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
from unittest.mock import patch

from support import DatabaseTestCase
from steve.election import Election, ElectionBadState, ElectionNotFound, IssueNotFound
from steve.persondb import PersonDB


class ElectionTests(DatabaseTestCase):
    def test_mixed_election_counts_only_latest_votes_after_closure(self):
        election = self.create_election()
        yna = election.add_issue('Approve', None, 'yna', None)
        stv = self.add_stv_issue(election)
        election.add_voter('alice')
        election.add_voter('bob')
        election.open(self.pdb)
        election.add_votes('alice', {yna: 'n', stv: 'a,b'})
        election.add_vote('alice', yna, 'y')
        election.add_votes('bob', {yna: 'a', stv: 'a'})
        with self.assertRaises(ElectionBadState):
            election.tally_issue(yna)
        election.close()
        self.assertFalse(election.is_tampered(self.pdb))
        result, voters = election.tally_issue(yna)
        self.assertEqual(result[1], {'y': 1, 'n': 0, 'a': 1})
        self.assertEqual(voters, {'alice', 'bob'})
        result, _ = election.tally_issue(stv)
        self.assertEqual(result[1]['candidates'], {'a': True, 'b': False})
        with self.assertRaises(ElectionBadState):
            election.add_vote('alice', yna, 'n')

    def test_invalid_or_ineligible_issue_rejects_entire_ballot(self):
        election = self.create_election()
        yna = election.add_issue('Approve', '', 'yna', None)
        stv = self.add_stv_issue(election)
        election.add_voter('alice')
        election.add_voter('bob', yna)
        election.open(self.pdb)
        for ranking in ('unknown', 'a,a', 'a,,b'):
            with self.subTest(ranking=ranking), self.assertRaises(ValueError):
                election.add_votes('alice', {yna: 'y', stv: ranking})
        with self.assertRaises(PermissionError):
            election.add_votes('bob', {yna: 'y', stv: 'a'})
        self.assertFalse(any(election.has_voted_upon('alice').values()))
        self.assertFalse(any(election.has_voted_upon('bob').values()))
        election.add_votes('alice', {yna: 'y', stv: ''})
        with self.assertRaises(ValueError):
            election.add_votes('alice', {yna: 'n', stv: 'unknown'})
        election.close()
        self.assertEqual(election.tally_issue(yna)[0][1]['y'], 1)

    def test_ambiguous_stv_configuration_does_not_create_an_issue(self):
        election = self.create_election()
        for kv in (
            {'seats': 1, 'labelmap': {'a': 'Same name', 'b': 'Same name'}},
            {'seats': 0, 'labelmap': {'a': 'Alice', 'b': 'Bob'}},
        ):
            with self.subTest(kv=kv), self.assertRaises(ValueError):
                election.add_issue('Invalid election', '', 'stv', kv)
        self.assertEqual(election.list_issues(), [])

    def test_stv_can_elect_all_candidates_when_seats_exceed_candidates(self):
        election = self.create_election()
        iid = election.add_issue(
            'Uncontested seats',
            '',
            'stv',
            {'seats': 3, 'labelmap': {'a': 'Alice', 'b': 'Bob'}},
        )
        election.open(self.pdb)
        election.close()
        result, _ = election.tally_issue(iid)
        self.assertEqual(result[1]['candidates'], {'a': True, 'b': True})

    def test_storage_failure_rolls_back_earlier_votes(self):
        election = self.create_election()
        first = election.add_issue('First', '', 'yna', None)
        second = election.add_issue('Second', '', 'yna', None)
        election.add_voter('alice')
        election.open(self.pdb)
        election.db.conn.executescript("""
            CREATE TRIGGER fail_second_vote BEFORE INSERT ON vote
            WHEN (SELECT COUNT(*) FROM vote) > 0
            BEGIN SELECT RAISE(ABORT, 'Storage failure'); END;
        """)
        with self.assertRaises(sqlite3.IntegrityError):
            election.add_votes('alice', {first: 'y', second: 'n'})
        self.assertFalse(any(election.has_voted_upon('alice').values()))
        self.assertFalse(election.db.conn.in_transaction)

    def test_failed_opening_rolls_back_salts(self):
        election = self.create_election()
        election.add_issue('Approve', '', 'yna', None)
        election.add_voter('alice')
        with patch('steve.crypto.gen_opened_key', side_effect=RuntimeError('Failure')):
            with self.assertRaises(RuntimeError):
                election.open(self.pdb)
        self.assertTrue(election.is_editable())
        rows = election.db.conn.execute('SELECT salt FROM mayvote').fetchall()
        self.assertTrue(all(row['salt'] is None for row in rows))
        election.open(self.pdb)
        self.assertFalse(election.is_tampered(self.pdb))

    def test_failed_ballot_rolls_back_inside_a_caller_transaction(self):
        election = self.create_election()
        first = election.add_issue('First', '', 'yna', None)
        second = election.add_issue('Second', '', 'yna', None)
        election.add_voter('alice')
        election.open(self.pdb)
        election.db.conn.executescript("""
            CREATE TRIGGER fail_second_vote BEFORE INSERT ON vote
            WHEN (SELECT COUNT(*) FROM vote) > 0
            BEGIN SELECT RAISE(ABORT, 'Storage failure'); END;
        """)
        with election.db.conn:
            election.db.conn.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.IntegrityError):
                election.add_votes('alice', {first: 'y', second: 'n'})
            self.assertFalse(any(election.has_voted_upon('alice').values()))
            self.assertTrue(election.db.conn.in_transaction)
            election.add_vote('alice', first, 'n')
        election.close()
        self.assertEqual(election.tally_issue(first)[0][1]['n'], 1)
        self.assertEqual(election.tally_issue(second)[1], set())

    def test_concurrent_deletion_preserves_not_found_error_and_connection_ownership(
        self,
    ):
        election = self.create_election()
        with Election(self.db_path, election.eid) as other:
            other.delete()
        with self.assertRaises(ElectionNotFound):
            election.close()
        self.assertFalse(election.db.conn.in_transaction)
        self.assertIsNotNone(election.db.conn.execute('SELECT 1').fetchone())

    def test_delete_keeps_an_outer_transaction_open_until_the_caller_commits(self):
        election = self.create_election()
        with election.db.conn:
            election.db.conn.execute('BEGIN IMMEDIATE')
            election.delete()
            self.assertTrue(election.db.conn.in_transaction)
        self.assertEqual(Election.owned_elections(self.db_path, 'alice'), [])

    def test_database_rollback_preserves_the_original_error(self):
        election = self.create_election()
        iid = election.add_issue('Approve', '', 'yna', None)
        election.add_voter('alice')
        election.open(self.pdb)
        election.db.conn.executescript("""
            CREATE TRIGGER fail_vote BEFORE INSERT ON vote
            BEGIN SELECT RAISE(ROLLBACK, 'Storage rolled back transaction'); END;
        """)
        with election.db.conn:
            election.db.conn.execute('BEGIN IMMEDIATE')
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'Storage rolled back'):
                election.add_vote('alice', iid, 'y')
        self.assertFalse(any(election.has_voted_upon('alice').values()))

    def test_issue_operations_cannot_cross_election_boundaries(self):
        first = self.create_election()
        second = self.create_election('bob')
        iid = second.add_issue('Private issue', '', 'yna', None)
        operations = [
            lambda: first.get_issue(iid),
            lambda: first.edit_issue(iid, 'Changed', '', 'yna', None),
            lambda: first.delete_issue(iid),
            lambda: first.add_voter('alice', iid),
        ]
        for operation in operations:
            with self.assertRaises(IssueNotFound):
                operation()
        self.assertEqual(second.get_issue(iid)[0], 'Private issue')
        first.open(self.pdb)
        first.close()
        with self.assertRaises(IssueNotFound):
            first.tally_issue(iid)

    def test_non_collision_integrity_error_does_not_retry(self):
        with patch('steve.crypto.create_id', side_effect=['0123456789']) as create_id:
            with self.assertRaises(sqlite3.IntegrityError):
                Election.create(self.db_path, 'Invalid owner', 'missing')
        self.assertEqual(create_id.call_count, 1)

    def test_collision_retries_without_overwriting_existing_election(self):
        existing = self.create_election()
        with patch('steve.crypto.create_id', side_effect=[existing.eid, '0123456789']):
            with Election.create(self.db_path, 'New election', 'bob') as created:
                self.assertEqual(created.get_metadata().owner_pid, 'bob')
        self.assertEqual(existing.get_metadata().owner_pid, 'alice')

    def test_issue_deletion_removes_eligibility_and_person_references_are_enforced(
        self,
    ):
        election = self.create_election()
        iid = election.add_issue('Approve', '', 'yna', None)
        election.add_voter('bob')
        with self.assertRaises(sqlite3.IntegrityError):
            self.pdb.delete_person('bob')
        election.delete_issue(iid)
        self.pdb.delete_person('bob')
        self.assertEqual(election.get_voters_for_email(), [])

    def test_contexts_close_owned_connections_but_preserve_borrowed_connections(self):
        with Election.create(self.db_path, 'Owned', 'alice') as owned:
            connection = owned.db.conn
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute('SELECT 1')
        db = Election.open_database(self.db_path)
        self.addCleanup(db.conn.close)
        with db.conn:
            db.conn.execute('BEGIN IMMEDIATE')
            with Election.create(self.db_path, 'Borrowed', 'alice', db=db) as borrowed:
                self.assertTrue(borrowed.is_editable())
            with PersonDB(self.pdb.db) as borrowed_persondb:
                self.assertEqual(borrowed_persondb.get_person('alice')[0], 'Alice')
            self.assertTrue(db.conn.in_transaction)
        self.assertIsNotNone(db.conn.execute('SELECT 1').fetchone())

    def test_opened_election_rejects_edits_with_explicit_state_error(self):
        election = self.create_election()
        iid = election.add_issue('Approve', '', 'yna', None)
        election.open(self.pdb)
        for operation in (
            lambda: election.add_issue('Other', '', 'yna', None),
            lambda: election.edit_issue(iid, 'Changed', '', 'yna', None),
            lambda: election.add_voter('bob'),
            lambda: election.delete_issue(iid),
            election.delete,
            lambda: election.open(self.pdb),
        ):
            with self.assertRaises(ElectionBadState):
                operation()
