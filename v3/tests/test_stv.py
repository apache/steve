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

import types
import unittest
from unittest import mock

import steve.vtypes.stv


class CandidateTests(unittest.TestCase):
    def test_version_one_candidate_has_no_asfid(self):
        candidates = steve.vtypes.stv.get_candidates({'labelmap': {'a': 'Alice'}})

        self.assertEqual(candidates, {'a': {'asfid': '', 'name': 'Alice'}})

    def test_version_two_candidate_includes_asfid(self):
        candidates = steve.vtypes.stv.get_candidates(
            {'version': 2, 'labelmap': {'a': ['alice', 'Alice']}}
        )

        self.assertEqual(candidates, {'a': {'asfid': 'alice', 'name': 'Alice'}})

    def test_version_two_candidate_requires_pair(self):
        with self.assertRaisesRegex(ValueError, r'\[asfid, name\] pair'):
            steve.vtypes.stv.get_candidates(
                {'version': 2, 'labelmap': {'a': ['alice']}}
            )

    def test_unknown_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported STV KV version: 3'):
            steve.vtypes.stv.get_candidates({'version': 3, 'labelmap': {}})

    def test_tally_uses_names_from_all_candidate_versions(self):
        def run_stv(names, votes, seats):
            self.assertEqual(names, ['Alice', 'Bob'])
            self.assertEqual(votes, [['Alice', 'Bob']])
            self.assertEqual(seats, 1)
            return types.SimpleNamespace(
                l=[
                    types.SimpleNamespace(
                        name='Alice', status=steve.vtypes.stv.stv_tool.ELECTED
                    ),
                    types.SimpleNamespace(
                        name='Bob', status=steve.vtypes.stv.stv_tool.ELIMINATED
                    ),
                ]
            )

        labelmaps = {
            1: {'a': 'Alice', 'b': 'Bob'},
            2: {'a': ['alice', 'Alice'], 'b': ['bob', 'Bob']},
        }
        for version, labelmap in labelmaps.items():
            with self.subTest(version=version):
                kv = {'version': version, 'labelmap': labelmap, 'seats': 1}
                with mock.patch.object(steve.vtypes.stv.stv_tool, 'run_stv', run_stv):
                    _, data = steve.vtypes.stv.tally(['a,b'], kv)

                self.assertEqual(data['candidates'], {'a': True, 'b': False})
                self.assertEqual(data['version'], version)
                self.assertEqual(data['labelmap'], labelmap)


if __name__ == '__main__':
    unittest.main()
