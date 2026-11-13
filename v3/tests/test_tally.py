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

import json
import subprocess
import sys

from support import DatabaseTestCase, ROOT


class TallyTests(DatabaseTestCase):
    def test_tally_cli_outputs_json_and_refuses_tampered_election(self):
        election = self.create_election()
        iid = election.add_issue('Approve', '', 'yna', None)
        election.add_voter('alice')
        election.open(self.pdb)
        election.add_vote('alice', iid, 'y')
        election.close()
        command = [
            sys.executable,
            str(ROOT / 'server/bin/tally.py'),
            '--db-path',
            str(self.db_path),
            '--issue-id',
            iid,
            '--output',
            'json',
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual(
            data['results'][iid]['supporting_data'], {'y': 1, 'n': 0, 'a': 0}
        )
        self.assertEqual(data['voters'], ['alice'])
        election.db.conn.execute(
            'UPDATE issue SET title = ? WHERE iid = ?', ('Changed', iid)
        )
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, '')
        self.assertTrue(result.stderr)
