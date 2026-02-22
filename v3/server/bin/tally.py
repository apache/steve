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

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DEFAULT_DB_FNAME = THIS_DIR.parent / 'steve.db'


def list_elections(db_fname, spy_on_open):
    """
    List elections available for tallying.
    Returns a list of (eid, title, close_at, state) tuples, sorted by close_at descending.
    Includes closed elections, or open ones if spy_on_open is True.
    """
    eids = steve.election.Election.list_closed_election_ids(db_fname, include_open=spy_on_open)
    
    elections = []
    for eid in eids:
        election = steve.election.Election(db_fname, eid)
        metadata = election.get_metadata()
        elections.append((eid, metadata.title, metadata.close_at, metadata.state))
    
    # Sort by close_at descending (most recent first)
    elections.sort(key=lambda x: x[2] or 0, reverse=True)
    return elections


def select_election(elections):
    """
    Interactively prompt the admin to select an election from the list.
    Returns the selected eid, or None if none available.
    """
    if not elections:
        print("No elections available for tallying.")
        return None
    
    print("Available elections (sorted by close date, most recent first):")
    for i, (eid, title, close_at, state) in enumerate(elections, 1):
        close_str = datetime.datetime.fromtimestamp(close_at).strftime('%Y-%m-%d %H:%M') if close_at else 'N/A'
        print(f"{i}. {eid} - {title} (Closed: {close_str}, State: {state})")
    
    while True:
        try:
            choice = input("Select an election by number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(elections):
                return elections[idx][0]
            else:
                print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number or 'q'.")


def tally_election(election, output_format):
    """
    Tally all issues in the given election and output results.
    """
    issues = election.list_issues()
    if not issues:
        print("No issues to tally in this election.")
        return
    
    results = {}
    for issue in issues:
        try:
            tally_result = election.tally_issue(issue.iid)
            results[issue.iid] = {
                'title': issue.title,
                'vtype': issue.vtype,
                'human_result': tally_result[0],
                'supporting_data': tally_result[1]
            }
        except Exception as e:
            print(f"Error tallying issue {issue.iid}: {e}")
            raise  # Fail hard
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
    else:  # text
        for iid, data in results.items():
            print(f"Issue {iid}: {data['title']} ({data['vtype']})")
            print(f"Result: {data['human_result']}")
            print(f"Details: {data['supporting_data']}")
            print("-" * 40)


def main(spy_on_open, election_id, db_fname, output_format):
    """
    Main function to run the tally script.
    """
    if election_id:
        election = steve.election.Election(db_fname, election_id)
    else:
        elections = list_elections(db_fname, spy_on_open)
        election_id = select_election(elections)
        if not election_id:
            print("No election selected. Exiting.")
            return
        election = steve.election.Election(db_fname, election_id)
    
    # Check for tampering
    pdb = steve.persondb.PersonDB.open(db_fname)
    if election.is_tampered(pdb):
        print(f"Error: Election {election_id} has been tampered with. Cannot proceed.")
        sys.exit(1)
    
    # Proceed with tally
    tally_election(election, output_format)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Tally votes for all issues in a closed election (or open if --spy-on-open-elections is used)."
    )
    parser.add_argument(
        '--spy-on-open-elections',
        action='store_true',
        help='Allow tallying of open elections (use with caution).'
    )
    parser.add_argument(
        '--election-id',
        help='Specify election ID to tally directly (skips interactive selection).'
    )
    parser.add_argument(
        '--db-path',
        default=str(DEFAULT_DB_FNAME),
        help='Path to the database file.'
    )
    parser.add_argument(
        '--output',
        choices=['text', 'json'],
        default='text',
        help='Output format for results.'
    )
    args = parser.parse_args()

    main(args.spy_on_open_elections, args.election_id, args.db_path, args.output)
