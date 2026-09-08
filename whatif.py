#!/usr/bin/env python3
#
#####
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#####

# Run alternate voting scenarios: vary the number of seats, remove candidates,
# or do a run-off with only the specified candidates.  Candidate names can
# be specified using either their first name, last name, or full name without
# any spaces (independent of case).  Examples:
#
#   whatif.py ../Meetings/20110712/raw_board_votes.txt 10
#   whatif.py ../Meetings/20110712/raw_board_votes.txt -LawrenceRosen
#   whatif.py ../Meetings/20110712/raw_board_votes.txt 1 kulp noirin geir chris
#
# whatif.rb depends on this positional argv shape. Keep it.

import sys
if __name__ != '__main__':
    raise Exception('ERROR: not intended to be used as a library.')

import argparse
import re
import pathlib

THIS_SCRIPT = pathlib.Path(__file__).resolve()
THIS_DIR = THIS_SCRIPT.parent

sys.path.append(str(THIS_DIR / 'monitoring'))
import stv_tool


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog=THIS_SCRIPT.name,
        description='Run alternate STV scenarios (seats, drop, runoff).',
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Verbose STV tracing',
    )
    parser.add_argument('votefile', help='vote-results.json or raw_board_votes.txt')
    parser.add_argument(
        'rest', nargs=argparse.REMAINDER,
        help='[seats] [name ...] or [seats] [-name ...]',
    )
    return parser.parse_args(argv)


args = parse_args(sys.argv[1:])
if args.verbose:
    stv_tool.VERBOSE = True

data = stv_tool.LoadData.from_path(args.votefile)
names = list(data.names)
votes = data.votes

rest = list(args.rest)
if rest and rest[0].isdigit():
    seats = int(rest.pop(0))
else:
    seats = 9

alias = {}
for name in names:
    lname = re.sub(r'[^\w ]', '', name.lower())
    alias[lname.replace(' ', '')] = name
    for part in lname.split(' '):
        alias[part] = name

for arg in rest:
    if arg.lstrip('-').lower() not in alias:
        sys.stderr.write('invalid selection: %s\n' % arg)
        sys.exit(1)

if not rest:
    pass
elif rest[0][0] == '-':
    for name in rest:
        names.remove(alias[name.lstrip('-').lower()])
else:
    names = [alias[n.lower()] for n in sorted(rest)]

trimmed = []
for voteseq in votes:
    newseq = [v for v in voteseq if v in names]
    if newseq:
        trimmed.append(newseq)

candidates = stv_tool.run_stv(names, trimmed, seats)
candidates.print_results()
print('Done!')
