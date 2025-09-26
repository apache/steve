#!/usr/bin/env python3
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
# ----
#
# ### TBD: DOCCO
# USAGE: run_stv.py .../Meetings/yyyymmdd
#

import sys
import os.path

# Ensure that we can import the "steve" package.
THIS_DIR = os.path.realpath(os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(THIS_DIR))
import steve.vtypes.stv

# The stv module loads the stv_tool module. Tweak it.
stv_tool = steve.vtypes.stv.stv_tool
stv_tool.VERBOSE = True


def main(mtgdir):
    rawfile = os.path.join(mtgdir, 'raw_board_votes.txt')
    labelfile = os.path.join(mtgdir, 'board_nominations.ini')

    assert os.path.exists(rawfile)
    assert os.path.exists(labelfile)

    labelmap = stv_tool.read_labelmap(labelfile)
    votes = stv_tool.read_votefile(rawfile).values()

    # Construct a label-sorted list of names from the labelmap.
    names = [name for _, name in sorted(labelmap.items())]

    kv = {
        'labelmap': labelmap,
        'seats': 9,
        }

    # NOTE: for backwards-compat, the tally() function accepts a
    # list of names with caller-defined sorting.
    human, _ = steve.vtypes.stv.tally(votes, kv, names)

    # For the comparison purposes:
    print(human)
    print('Done!')


if __name__ == '__main__':
    main(sys.argv[1])
