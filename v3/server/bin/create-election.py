#!/usr/bin/env -S uv run --script

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

"""
Script to create an election from a YAML definition file.
Reads election metadata, issues, and voter records, then populates the database.
"""

import argparse
import datetime
import pathlib
import logging
from contextlib import closing
import yaml

import steve.election
import steve.vtypes.stv

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR.parent / 'steve.db'

# Supported vote types
VALID_VTYPES = {'yna', 'stv'}


def parse_datetime(dt):
    """Parse timestamps or YAML/ISO dates, interpreting timezone-free values as UTC."""
    if dt is None:
        return None
    if type(dt) is int:
        return dt
    if isinstance(dt, str):
        dt = datetime.datetime.fromisoformat(dt)
    if isinstance(dt, datetime.date) and not isinstance(dt, datetime.datetime):
        dt = datetime.datetime.combine(dt, datetime.time())
    if isinstance(dt, datetime.datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return int(dt.timestamp())
    raise ValueError(f'Invalid datetime format: {dt}')


def validate_issue(issue):
    """Validate an issue dict from YAML."""
    if not isinstance(issue, dict):
        raise ValueError('Each issue must be a mapping')
    if not isinstance(issue.get('vtype'), str) or issue['vtype'] not in VALID_VTYPES:
        raise ValueError(f'Invalid vtype: {issue.get("vtype")}')
    if not isinstance(issue.get('title'), str) or not issue['title'].strip():
        raise ValueError('Each issue must have a title')
    if issue.get('description') is not None and not isinstance(
        issue['description'], str
    ):
        raise ValueError('Issue description must be a string')
    if issue['vtype'] == 'stv':
        steve.vtypes.stv.validate_configuration(issue.get('kv'))
    return issue


def main(yaml_file):
    with open(yaml_file, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or not isinstance(data.get('election'), dict):
        raise ValueError('YAML must contain an election mapping')

    # Extract election data
    election_data = data.get('election', {})
    title = election_data.get('title')
    owner_pid = election_data.get('owner_pid')
    authz = election_data.get('authz')
    open_at = parse_datetime(election_data.get('open_at'))
    close_at = parse_datetime(election_data.get('close_at'))

    if (
        not isinstance(title, str)
        or not title.strip()
        or not isinstance(owner_pid, str)
        or not owner_pid.strip()
    ):
        raise ValueError('Election must have title and owner_pid')
    if authz is not None and not isinstance(authz, str):
        raise ValueError('authz must be a string')

    # Extract issues
    issues = data.get('issues', [])
    if not isinstance(issues, list):
        raise ValueError('issues must be a list')
    for issue in issues:
        validate_issue(issue)

    # Extract record: list of pid values for eligible voters
    record = data.get('record', [])
    if not isinstance(record, list) or any(not isinstance(pid, str) for pid in record):
        raise ValueError('record must be a list of pid values')
    if len(set(record)) != len(record):
        raise ValueError('record contains duplicate pid values')

    db = steve.election.Election.open_database(DB_FNAME)
    with closing(db.conn), db.conn:
        db.conn.execute('BEGIN IMMEDIATE')
        for pid in {owner_pid, *record}:
            if not db.conn.execute(
                'SELECT 1 FROM person WHERE pid = ?', (pid,)
            ).fetchone():
                raise ValueError(f'PID {pid} not found in person database')
        election = steve.election.Election.create(
            DB_FNAME, title, owner_pid, authz, open_at, close_at, db=db
        )
        for issue_data in issues:
            election.add_issue(
                issue_data['title'],
                issue_data.get('description'),
                issue_data['vtype'],
                issue_data.get('kv') if issue_data['vtype'] == 'stv' else None,
            )
        for pid in record:
            election.add_voter(pid)
    _LOGGER.info(
        f'Created election[E:{election.eid}] with {len(record)} eligible voters'
    )
    return election.eid


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
