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

import os.path
import importlib.util

# Where can we find the stv_tool module?
STV_RELPATH = '../../../monitoring/stv_tool.py'


def load_stv():
    pathname = os.path.join(os.path.dirname(__file__), STV_RELPATH)
    spec = importlib.util.spec_from_file_location('stv_tool', pathname)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# load_stv() loads the module (again) on each call. Each one is separate,
# with (eg.) a distinct VERBOSE flag. Note that sys.modules is completely
# uninvolved in this process. Thus, let's load this once. (this is
# effectively a fancy "import" statement)
stv_tool = load_stv()


def tally(votestrings, kv):
    """
    Run the STV tally process.

    votestrings: List of strings, each representing a voter's preferences as comma-separated labels
                 (e.g., 'a,b,c' for votes in order of preference). Labels must match keys in kv['labelmap'].
    kv: Dict containing STV configuration.
        - 'version': Integer version of the kv format (currently 1).
        - 'labelmap': Dict mapping single-character labels to candidate names (e.g., {'a': 'Alice'}).
        - 'seats': Integer number of seats to elect.
    """

    # kv['labelmap'] should be: LABEL: NAME
    # for example: { 'a': 'John Doe', }
    labelmap = kv['labelmap']
    revmap = { v: k for k, v in labelmap.items() }

    seats = kv['seats']

    # Remap all votestrings from comma-separated label strings into sequences of NAMEs.
    # Split on commas, strip whitespace, and filter out empty parts.
    votes = [
        [labelmap[label.strip()] for label in v.split(',') if label.strip()]
        for v in votestrings
    ]

    # Use sorted names for reproducible ordering.
    names = sorted(labelmap.values())
    results = stv_tool.run_stv(names, votes, seats)

    human = '\n'.join(
        f'{c.name:40}{" " if c.status == stv_tool.ELECTED else " not "}elected'
        for c in results.l
    )
    data = {
        # LABEL: ELECTED-BOOL
        'candidates': { revmap[cand.name]: (cand.status == stv_tool.ELECTED)
                        for cand in results.l },

        # Carry the input configuration and votestrings into the result.
        'labelmap': labelmap,
        'seats': seats,
        'votestrings': [ vs for vs in votestrings if vs ],  # Eliminate empty
    }
    return human, data
