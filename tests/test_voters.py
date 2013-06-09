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
import os

from brownie.datastructures import Counter

from steve.voters import get_group


DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')


def test_duplicates():
    voters = get_group(os.path.join(DATA_DIR, 'duplicates.txt'))

    assert len(voters) == 3
    assert 'a@b.com' in voters
    assert 'c@d.com' in voters
    assert 'a@b.com' in [x for x, y in Counter(voters).items() if y > 1]

