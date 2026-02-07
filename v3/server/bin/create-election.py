#!/usr/bin/env python3

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

import argparse
import datetime
import pathlib
import logging
import yaml

import steve.election
import steve.persondb

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR.parent / 'steve.db'

# Supported vote types
VALID_VTYPES = {'yna', 'stv'}


def parse_datetime(dt_str):
    """Parse ISO datetime string to Unix timestamp."""
    if not dt_str:
        return None
    dt = datetime.datetime.fromisoformat(dt_str)
    return int(dt.timestamp())


def validate_issue(issue):
    """Validate an issue dict from YAML."""
    if 'vtype' not in issue or issue['vtype'] not in VALID_VTYPES:
        raise ValueError(f'Invalid vtype: {issue.get("vtype")}')
    if issue['vtype'] == 'stv':
        kv = issue.get('kv', {})
        if not all(k in kv for k in ['version', 'labelmap', 'seats']):
            raise ValueError(
                'STV issue missing required kv fields: version, labelmap, seats'
            )
        if not isinstance(kv['seats'], int) or kv['seats'] <= 0:
            raise ValueError('STV seats must be a positive integer')
    return issue


def main(yaml_file):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    # Extract election data
    election_data = data.get('election', {})
    title = election_data.get('title')
    owner_pid = election_data.get('owner_pid')
    authz = election_data.get('authz')
    open_at = parse_datetime(election_data.get('open_at'))
    close_at = parse_datetime(election_data.get('close_at'))

    if not title or not owner_pid:
        raise ValueError('Election must have title and owner_pid')

    # Extract issues
    issues = data.get('issues', [])
    for issue in issues:
        validate_issue(issue)

    # Extract voters tag (placeholder: assume "members" means all persons)
    eligible_voters = data.get('eligible_voters')
    if eligible_voters != 'members':
        raise ValueError("Only 'members' is supported for eligible_voters")

    ### revising how we manage the two database instances and their
    ### connections. no transactions for now. partial Elections, and
    ### issues are fine for now.
    # Start transaction for safety
    # pdb = steve.persondb.PersonDB(DB_FNAME)
    # pdb.db.conn.execute('BEGIN TRANSACTION')

    try:
        # Create election
        election = steve.election.Election.create(
            DB_FNAME, title, owner_pid, authz, open_at, close_at
        )
        _LOGGER.info(
            f'Created election[E:{election.eid}]: "{title}" by owner "{owner_pid}"'
        )

        # Add issues
        for issue_data in issues:
            iid = election.add_issue(
                issue_data['title'],
                issue_data.get('description'),
                issue_data['vtype'],
                issue_data.get('kv') if issue_data['vtype'] == 'stv' else None,
            )
            _LOGGER.info(f'Added issue[I:{iid}] to election[E:{election.eid}]')

        # Open a PersonDB using the existing DB from the Election
        pdb = steve.persondb.PersonDB(election.db)

        ### HACK: we opened PDB using the existing DB from the Election.
        ### It does not have the cursors specific to PersonDB. For now,
        ### hack the bugger in.
        ### q_person: SELECT * FROM person ORDER BY pid
        pdb.q_person = pdb.db.cursor_for('SELECT * FROM person ORDER BY pid')

        # Add voters: All persons in persondb to all issues
        all_persons = pdb.list_persons()
        for person in all_persons:
            election.add_voter(person.pid)
        _LOGGER.info(f'Added {len(all_persons)} voters to election[E:{election.eid}]')

        ### we aren't doing transactions right now. omit this.
        # pdb.db.conn.execute('COMMIT')
        _LOGGER.info(f'Election[E:{election.eid}] fully created from {yaml_file}')

    except Exception as e:
        ### we aren't doing transactions right now. omit this.
        # pdb.db.conn.execute('ROLLBACK')
        _LOGGER.error(f'Failed to create election from {yaml_file}: {e}')
        raise


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'yaml_file',
        help='Path to the YAML file defining the election.',
    )
    args = parser.parse_args()
    main(args.yaml_file)
