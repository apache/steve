#!/usr/bin/env python3
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# Load a bunch of fake data into the database, for stuff to work with.


import argparse
import sqlite3
import sys
import pathlib
import logging

import faker  # pip3 install faker

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR.parent / 'steve.db'

sys.path.insert(0, str(THIS_DIR.parent.parent))
import steve.election  # noqa: E402

### we shouldn't need this. do so, for now.
import steve.crypto  # noqa: E402

# Do we need individual instances? Use a singleton for now.
FAKE = faker.Faker()


def main(args):
    owner_pid = args.owner_pid
    if not owner_pid:
        owner_pid = random_owner()

    for _ in range(args.elections):
        gen_election(owner_pid, args.issues)


def gen_election(owner_pid, issue_count=10):
    title = FAKE.sentence()
    e = steve.election.Election.create(DB_FNAME, title, owner_pid)
    _LOGGER.info(f'Created election[E:{e.eid}]: "{title}",'
                 f' by owner "{owner_pid}"')

    for _ in range(issue_count):
        title = FAKE.sentence()
        description = FAKE.paragraph()
        vtype = 'yna'  ### something else?
        kv = None  ### something else?

        ### grr. this should be internal
        iid = steve.crypto.create_id()
        e.add_issue(iid, title, description, vtype, kv)
        _LOGGER.info(f'[E:{e.eid}]: created issue[I:{iid}]: "{title}"')


def random_owner():
    """Pick a random PID from those available."""

    conn = sqlite3.connect(DB_FNAME)
    cursor = conn.execute('SELECT pid FROM person ORDER BY RANDOM() LIMIT 1')
    pid = cursor.fetchone()[0]
    conn.close()

    return pid


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--elections', type=int, required=False, default=10,
                        help="The number of elections to create.")
    parser.add_argument('--issues', type=int, required=False, default=10,
                        help="The number of issues per election to create.")
    parser.add_argument('--owner-pid', type=str, required=False,
                        help="The owner's Apache ID to use for created elections."
                        " If not set, pick a random existing person.")

    main(parser.parse_args())
