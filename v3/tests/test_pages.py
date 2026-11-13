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
import tempfile
import time
import unittest
from html.parser import HTMLParser
from unittest.mock import patch

import asfquart

from support import DatabaseTestCase, ROOT


class Forms(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = {}
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.current = {'method': attrs.get('method', 'GET'), 'fields': {}}
            self.forms[attrs.get('action', '')] = self.current
        elif tag == 'input' and self.current is not None and attrs.get('name'):
            self.current['fields'][attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None


class PageTests(DatabaseTestCase, unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_directory = tempfile.TemporaryDirectory(prefix='steve-http-test-')
        cls.addClassCleanup(cls.app_directory.cleanup)
        cls.app = asfquart.construct(
            'steve-tests', app_dir=cls.app_directory.name, token_file=None, oauth=False
        )
        cls.app.cfg.db = 'unused.db'
        cls.app.config['TESTING'] = True
        spec = importlib.util.spec_from_file_location(
            'test_server_pages', ROOT / 'server/pages.py'
        )
        assert spec is not None and spec.loader is not None
        cls.pages = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pages)

    def setUp(self):
        super().setUp()
        db_patch = patch.object(self.pages, 'DB_FNAME', self.db_path)
        db_patch.start()
        self.addCleanup(db_patch.stop)

    async def asyncSetUp(self):
        self.client = self.app.test_client()
        await self.login('alice')

    async def login(self, pid):
        async with self.client.session_transaction(scheme='https') as session:
            session.clear()
            session[self.app.app_id] = {
                'uid': pid,
                'fullname': pid.title(),
                'pmcs': ['example'],
                'uts': time.time(),
            }
        response = await self.client.get('/admin', scheme='https')
        self.assertEqual(response.status_code, 200)
        forms = Forms(await response.get_data(as_text=True))
        self.csrf = forms.forms['/do-create-election']['fields']['csrf_token']

    async def post(self, path, *, form=None, json=None):
        if json is not None:
            return await self.client.post(
                path, json=json, headers={'X-CSRFToken': self.csrf}, scheme='https'
            )
        return await self.client.post(
            path, form={'csrf_token': self.csrf, **(form or {})}, scheme='https'
        )

    async def test_create_form_and_owner_lifecycle_work_with_csrf(self):
        response = await self.post(
            '/do-create-election', form={'title': 'A real election'}
        )
        self.assertEqual(response.status_code, 303)
        location = response.headers['Location']
        eid = location.rsplit('/', 1)[-1]
        response = await self.client.get(location, scheme='https')
        self.assertEqual(response.status_code, 200)
        forms = Forms(await response.get_data(as_text=True))
        opening = forms.forms[f'/do-open/{eid}']
        response = await self.client.open(
            f'/do-open/{eid}',
            method=opening['method'],
            form=opening['fields'],
            scheme='https',
        )
        self.assertEqual(response.status_code, 303)
        response = await self.client.get(location, scheme='https')
        closing = Forms(await response.get_data(as_text=True)).forms[f'/do-close/{eid}']
        response = await self.client.open(
            f'/do-close/{eid}',
            method=closing['method'],
            form=closing['fields'],
            scheme='https',
        )
        self.assertEqual(response.status_code, 303)
        response = await self.post(f'/do-close/{eid}')
        self.assertEqual(response.status_code, 409)

    async def test_csrf_rejects_missing_wrong_and_other_session_tokens(self):
        for token in (None, 'wrong', '\N{SNOWMAN} token'):
            form = {'title': 'Rejected'}
            if token is not None:
                form['csrf_token'] = token
            response = await self.client.post(
                '/do-create-election', form=form, scheme='https'
            )
            self.assertEqual(response.status_code, 400)
        previous = self.csrf
        await self.login('bob')
        response = await self.client.post(
            '/do-create-election',
            form={'title': 'Rejected', 'csrf_token': previous},
            scheme='https',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.pages.steve.election.Election.owned_elections(self.db_path, 'alice'),
            [],
        )

    async def test_unrelated_committer_cannot_manage_election(self):
        election = self.create_election()
        iid = election.add_issue('Approve', '', 'yna', None)
        stv = self.add_stv_issue(election)
        await self.login('bob')
        for path in (f'/manage/{election.eid}', f'/manage-stv/{election.eid}/{stv}'):
            response = await self.client.get(path, scheme='https')
            self.assertEqual(response.status_code, 403)
        for path in (
            f'/do-open/{election.eid}',
            f'/do-close/{election.eid}',
            f'/do-add-issue/{election.eid}',
            f'/do-edit-issue/{election.eid}/{iid}',
            f'/do-delete-issue/{election.eid}/{iid}',
        ):
            response = await self.post(
                path, form={'title': 'Changed', 'description': ''}
            )
            self.assertEqual(response.status_code, 403)
        response = await self.post(
            f'/do-set-open_at/{election.eid}', json={'date': '2026-11-01'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(election.is_editable())
        self.assertEqual(election.get_issue(iid)[0], 'Approve')

    async def test_open_and_close_get_requests_never_change_state(self):
        election = self.create_election()
        for action in ('open', 'close'):
            response = await self.client.get(
                f'/do-{action}/{election.eid}', scheme='https'
            )
            self.assertEqual(response.status_code, 405)
        self.assertTrue(election.is_editable())

    async def test_issue_from_another_election_is_not_editable_through_owned_election(
        self,
    ):
        owned = self.create_election()
        other = self.create_election('bob')
        iid = other.add_issue('Other issue', '', 'yna', None)
        response = await self.post(
            f'/do-edit-issue/{owned.eid}/{iid}', form={'title': 'Changed'}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(other.get_issue(iid)[0], 'Other issue')

    async def test_date_validation_and_utc_roundtrip(self):
        election = self.create_election()
        path = f'/do-set-open_at/{election.eid}'
        for data in ([], {'date': 123}, {'date': 'not-a-date'}, {'date': ''}):
            response = await self.post(path, json=data)
            self.assertEqual(response.status_code, 400)
        response = await self.post(path, json={'date': '1970-01-01'})
        self.assertEqual(response.status_code, 204)
        response = await self.client.get(f'/manage/{election.eid}', scheme='https')
        self.assertIn('value="1970-01-01"', await response.get_data(as_text=True))
        response = await self.post(path, json={'date': '2026-11-01'})
        self.assertEqual(response.status_code, 204)
        expected = int(
            datetime.datetime(2026, 11, 1, tzinfo=datetime.timezone.utc).timestamp()
        )
        self.assertEqual(election.get_metadata().open_at, expected)
        response = await self.client.get(f'/manage/{election.eid}', scheme='https')
        html = await response.get_data(as_text=True)
        self.assertIn('value="2026-11-01"', html)
        election.open(self.pdb)
        response = await self.post(path, json={'date': '2026-12-01'})
        self.assertEqual(response.status_code, 409)
        response = await self.post(
            f'/do-set-close_at/{election.eid}', json={'date': '2026-12-01'}
        )
        self.assertEqual(response.status_code, 204)
        election.close()
        response = await self.post(
            f'/do-set-close_at/{election.eid}', json={'date': '2026-12-02'}
        )
        self.assertEqual(response.status_code, 409)

    async def test_voter_only_sees_eligible_issues_and_bad_ballot_is_atomic(self):
        election = self.create_election()
        public = election.add_issue('Eligible issue', None, 'yna', None)
        private = election.add_issue('Private issue', '', 'yna', None)
        election.add_voter('bob', public)
        election.open(self.pdb)
        await self.login('bob')
        response = await self.client.get(f'/vote-on/{election.eid}', scheme='https')
        self.assertEqual(response.status_code, 200)
        html = await response.get_data(as_text=True)
        self.assertIn('Eligible issue', html)
        self.assertNotIn('Private issue', html)
        response = await self.post(
            f'/do-vote/{election.eid}',
            form={f'vote-{public}': 'y', f'vote-{private}': 'n'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(any(election.has_voted_upon('bob').values()))
        response = await self.post(
            f'/do-vote/{election.eid}', form={f'vote-{public}': 'y'}
        )
        self.assertEqual(response.status_code, 303)
        self.assertTrue(election.has_voted_upon('bob')[public])

    async def test_invalid_stv_submission_is_rejected_before_any_issue_is_recorded(
        self,
    ):
        election = self.create_election()
        yna = election.add_issue('Approve', '', 'yna', None)
        stv = self.add_stv_issue(election)
        election.add_voter('alice')
        election.open(self.pdb)
        response = await self.post(
            f'/do-vote/{election.eid}',
            form={f'vote-{yna}': 'y', f'vote-{stv}': 'unknown'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(any(election.has_voted_upon('alice').values()))
