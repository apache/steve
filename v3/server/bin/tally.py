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

import argparse
import datetime
import pathlib
import logging
import json
import sys

import steve.election
import steve.persondb

from easydict import EasyDict as edict

try:
    import pbar
except ImportError:
    pbar = None

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_DB_FNAME = THIS_DIR.parent / 'steve.db'

# Self-annotate the format of a JSON output file.
RESULTS_VERSION = 1
# Future: document format changes across the versions.


def list_elections(db_fname, spy_on_open):
    """
    List elections available for tallying.
    Returns a list of edict objects with eid, title, close_at, state, issue_count, person_count.
    Includes closed elections, or open ones if spy_on_open is True.
    """
    eids = steve.election.Election.list_closed_election_ids(
        db_fname, include_open=spy_on_open
    )

    elections = []
    for eid in eids:
        election = steve.election.Election(db_fname, eid)
        metadata = election.get_metadata()
        # Fetch issue count using existing list_issues method
        issue_count = len(election.list_issues())
        # Fetch person count using existing get_voters_for_email method
        person_count = len(election.get_voters_for_email())
        elections.append(edict(
            eid=eid,
            title=metadata.title,
            close_at=metadata.close_at,
            state=metadata.state,
            issue_count=issue_count,
            person_count=person_count
        ))

    # Sort by close_at descending (most recent first)
    elections.sort(key=lambda x: x.close_at or 0, reverse=True)
    return elections


def select_election(elections):
    """
    Interactively prompt the admin to select an election from the list.
    Returns the selected eid, or None if none available.
    """
    if not elections:
        print('No elections available for tallying.')
        return None

    print('Available elections (sorted by close date, most recent first):')
    for i, election in enumerate(elections, 1):
        close_str = (
            datetime.datetime.fromtimestamp(election.close_at).strftime('%Y-%m-%d %H:%M')
            if election.close_at
            else 'N/A'
        )
        print(f'{i}. {election.eid} - {election.title} (Closed: {close_str}, State: {election.state}, Issues: {election.issue_count}, Eligible: {election.person_count})')

    while True:
        try:
            choice = input("Select an election by number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(elections):
                return elections[idx].eid
            else:
                print('Invalid choice. Try again.')
        except ValueError:
            print("Please enter a number or 'q'.")


def tally_election(election, issue_id, output_format):
    """
    Tally all issues in the given election and output results.
    """
    
    issues = election.list_issues()
    if not issues:
        _LOGGER.error('No issues to tally in this election.')
        return

    # Does the user want to just tally a single issue? (faster)
    if issue_id:
        issues = [issue for issue in issues if issue.iid == issue_id]
        if not issues:
            _LOGGER.error(f'Issue {issue_id} was not found.')
            return
        _LOGGER.info(f'Tallying one issue: {issue_id}')

    if len(issues) > 1:
        _LOGGER.info(f'Tallying {len(issues)} issues ...')

    all_voters = set()
    results = {}
    for issue in issues:
        try:
            tally_result, issue_voters = election.tally_issue(issue.iid)
            results[issue.iid] = {
                'title': issue.title,
                'vtype': issue.vtype,
                'human_result': tally_result[0],
                'supporting_data': tally_result[1],
            }
            all_voters.update(issue_voters)
        except Exception as e:
            print(f'Error tallying issue {issue.iid}: {e}')
            raise  # Fail hard

    if output_format == 'json':
        print(json.dumps(edict(version=RESULTS_VERSION,
                               results=results,
                               voters=sorted(all_voters),
                               ), indent=2))
    else:  # text
        for iid, data in results.items():
            print(f'Issue {iid}: {data["title"]} ({data["vtype"]})')
            print(f'Result: {data["human_result"]}')
            print(f'Details: {data["supporting_data"]}')
            print('-' * 40)


def main(spy_on_open, election_id, issue_id, db_fname, output_format):
    """
    Main function to run the tally script.
    """
    if issue_id:
        db = steve.election.Election.open_database(db_fname)
        issue = db.q_get_issue.first_row(issue_id)
        if not issue:
            raise steve.election.IssueNotFound(issue_id)
        election_id = issue.eid
        db.conn.close()
    elif not election_id:
        elections = list_elections(db_fname, spy_on_open)
        election_id = select_election(elections)
        if not election_id:
            print('No election selected. Exiting.')
            return

    election = steve.election.Election(db_fname, election_id)

    # Check for tampering
    pdb = steve.persondb.PersonDB.open(db_fname)
    if election.is_tampered(pdb):
        print(f'Error: Election {election_id} has been tampered with. Cannot proceed.')
        sys.exit(1)

    # Proceed with tally
    tally_election(election, issue_id, output_format)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='Tally votes for all issues in a closed election (or open if --spy-on-open-elections is used).',
    )
    parser.add_argument(
        '--spy-on-open-elections',
        action='store_true',
        help='Allow tallying of open elections (use with caution).',
    )
    parser.add_argument(
        '--election-id',
        help='Specify Election ID to tally directly (skips interactive selection).',
    )
    parser.add_argument(
        '--issue-id',
        help='Specify an Issue ID to tally directly (skips interactive selection).',
    )
    parser.add_argument(
        '--db-path', default=str(DEFAULT_DB_FNAME), help='Path to the database file.'
    )
    parser.add_argument(
        '--output',
        choices=['text', 'json'],
        default='text',
        help='Output format for results.',
    )
    args = parser.parse_args()

    if args.election_id and args.issue_id:
        _LOGGER.error('ISSUE_ID implies an ELECTION_ID; do not set both.')
        sys.exit(1)

    main(args.spy_on_open_elections, args.election_id, args.issue_id, args.db_path, args.output)
