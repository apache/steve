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
Script to send emails to all eligible voters for a given election.
Loads the election, renders an email template for each voter using EZT, and sends via asfpy.messaging.
"""

import argparse
import pathlib
import logging
import io

import ezt
import asfpy.messaging
import steve.election

_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR.parent / 'steve.db'


def main(eid, template_file):
    """
    Main function to load election, get voters, render emails, and send.
    """
    # Load the election
    election = steve.election.Election(DB_FNAME, eid)

    # Get metadata for context
    metadata = election.get_metadata()

    # Get list of eligible voters
    voters = election.get_voters_for_email()

    if not voters:
        _LOGGER.info(f'No eligible voters found for election {eid}')
        return

    # Load the EZT template
    template = ezt.Template(template_file, compress_whitespace=False)

    # Send email to each voter
    for voter in voters:
        # Prepare data dictionary for template rendering
        data = {
            'voter': voter,  # edict with pid, name, email
            'election': metadata,  # edict with eid, title, owner_pid, etc.
        }

        # Render the template to a StringIO stream
        output = io.StringIO()
        template.generate(output, data)
        rendered_body = output.getvalue()

        # Send the email
        asfpy.messaging.mail(
            sender='Apache Election Platform <voter@apache.org>',
            recipient=voter.email,
            subject=f'Vote in Election: {metadata.title}',
            message=rendered_body,
            # Add other parameters as needed (e.g., auth, headers)
        )

        _LOGGER.info(f'Sent email to {voter.email} for election {eid}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Send emails to eligible voters for a given election.',
    )
    parser.add_argument('--eid', required=True, help='Election ID to send emails for.')
    parser.add_argument(
        '--template',
        required=True,
        help='Path to the .ezt template file for email body.',
    )
    args = parser.parse_args()

    main(args.eid, args.template)
