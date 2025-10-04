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

import sys
import pathlib
import logging

import ldap  # pip3 install python-ldap
import asfpy.db
import asfpy.stopwatch
from easydict import EasyDict as edict

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR.parent / 'steve.db'

sys.path.insert(0, str(THIS_DIR.parent.parent))
import steve.persondb

# The ASF's LDAP server, available for read-only for finding potential voters.
LDAP_URL = 'ldaps://ldap-us.apache.org/'
LDAP_DN = 'ou=people,dc=apache,dc=org'
LDAP_ATTR = 'memberUid'


@asfpy.stopwatch.Stopwatch()
def main():
    pdb = steve.persondb.PersonDB(DB_FNAME)
    # Reach into PDB for the CONN, and start a transaction for all
    # of the inserts we will perform. (rather than default auto-commit)
    pdb.db.conn.execute('BEGIN TRANSACTION')

    client = ldap.initialize(LDAP_URL)
    binddn, bindpw = [ s.strip()
                       for s in open(THIS_DIR / 'bind.txt').readlines()[:2] ]
    #print('BIND:', binddn, bindpw)
    client.simple_bind_s(binddn, bindpw)

    with asfpy.stopwatch.Stopwatch('run LDAP full scan'):
        results = client.search_s(LDAP_DN, ldap.SCOPE_SUBTREE, 'uid=*', attrlist=None) #[LDAP_ATTR,])

    count = 0
    for r in results:
        # r[0] is the CN(?) ... not needed
        # r[1] is the {attr:[values..]} dict
        entry = edict(r[1])

        uid = entry.uid[0].decode('utf-8')
        visname = entry.cn[0].decode('utf-8')
        email = entry['asf-committer-email'][0].decode('utf-8')

        pdb.add_person(uid, visname, email)
        count += 1

    # Reach into the CONN and do the commit.
    pdb.db.conn.execute('COMMIT')

    _LOGGER.info(f'Loaded {count} persons into {DB_FNAME}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
