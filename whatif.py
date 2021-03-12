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
# Examples:
#   whatif.py ../Meetings/20110712/raw_board_votes.txt 10
#   whatif.py ../Meetings/20110712/raw_board_votes.txt -LawrenceRosen
#   whatif.py ../Meetings/20110712/raw_board_votes.txt 1 kulp noirin geir chris

import os.path
import sys
import re

sys.path.append(os.path.join(os.path.dirname(__file__), 'monitoring'))
import stv_tool

def usage():
  print('Usage: %s [-v] RAW_VOTES_FILE [seats] [-]name...' % scriptname)
  sys.exit(1)

if __name__ == '__main__':
  scriptname = sys.argv.pop(0)

  if sys.argv and sys.argv[0] == '-v':
    stv_tool.VERBOSE = True
    sys.argv.pop(0)

  # extract required vote file argument, and load votes from it
  if not sys.argv or not os.path.exists(sys.argv[0]): usage()
  votefile = sys.argv.pop(0)
  names, votes = stv_tool.load_votes(votefile)

  # extract optional number of seats argument
  if sys.argv and sys.argv[0].isdigit():
    seats = int(sys.argv.pop(0))
  else:
    seats = 9

  # extract an alias list of first, last, and joined names
  alias = {}
  for name in names:
    lname = re.sub('[^\w ]', '', name.lower())
    alias[lname.replace(' ', '')] = name
    for part in lname.split(' '):
      alias[part] = name

  # validate input
  for arg in sys.argv:
    if arg.lstrip('-').lower() not in alias:
      sys.stderr.write('invalid selection: %s\n' % arg)
      usage()

  if not sys.argv:
    # no changes to the candidates running
    pass
  elif sys.argv[0][0] == '-':
    # remove candidates from vote
    for name in sys.argv: names.remove(alias[name.lstrip('-').lower()])
  else:
    # only include specified candidates
    # NOTE: order is important, so sort the names for repeatability
    names = [ alias[n.lower()] for n in sorted(sys.argv) ]

  # Trim the raw votes based on cmdline params. Eliminate votes that
  # are not for one of the allowed names. Do not include voters who
  # did not vote for anybody [post-trimming].
  trimmed = { }
  for hashid, voteseq in votes.items():
    newseq = [ v for v in voteseq if v in names ]
    if newseq:
      trimmed[hashid] = newseq

  # run the vote
  candidates = stv_tool.run_vote(names, trimmed, seats)
  candidates.print_results()
  print('Done!')
