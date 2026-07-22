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


def get_candidates(kv):
    """Return normalized candidate details keyed by ballot label."""

    version = kv.get('version', 1)
    labelmap = kv['labelmap']

    if version == 1:
        candidates = {}
        for label, name in labelmap.items():
            if not isinstance(name, str):
                raise ValueError(f'STV v1 candidate {label!r} must be a name')
            candidates[label] = {'asfid': '', 'name': name}
    elif version == 2:
        candidates = {}
        for label, value in labelmap.items():
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                raise ValueError(
                    f'STV v2 candidate {label!r} must be an [asfid, name] pair'
                )
            asfid, name = value
            if not isinstance(asfid, str) or not isinstance(name, str):
                raise ValueError(
                    f'STV v2 candidate {label!r} must contain string values'
                )
            candidates[label] = {'asfid': asfid, 'name': name}
    else:
        raise ValueError(f'Unsupported STV KV version: {version}')

    return candidates


def tally(votestrings, kv):
    """
    Run the STV tally process.

    votestrings: List of strings, each representing a voter's preferences as comma-separated labels
                 (e.g., 'a,b,c' for votes in order of preference). Labels must match keys in kv['labelmap'].
    kv: Dict containing STV configuration.
        - 'version': Integer version of the kv format.
        - 'labelmap': Dict mapping labels to candidate details. Version 1 maps
          labels directly to names; version 2 maps labels to [asfid, name] pairs.
        - 'seats': Integer number of seats to elect.
    """

    # Trim the incoming votestrings: no empty strings:
    trimmed = [s for vs in votestrings if (s := vs.strip())]

    candidates = get_candidates(kv)
    labelmap = {label: candidate['name'] for label, candidate in candidates.items()}
    revmap = {name: label for label, name in labelmap.items()}

    seats = kv['seats']

    # Remap all votestrings from comma-separated label strings into sequences of NAMEs.
    # Split on commas, strip whitespace, and filter out empty parts.
    votes = [
        [
            labelmap[ballot_label]
            for label in vs.split(',')
            if (ballot_label := label.strip())
        ]
        for vs in trimmed
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
        'candidates': {
            revmap[cand.name]: (cand.status == stv_tool.ELECTED) for cand in results.l
        },
        # Carry the input configuration and votestrings into the result.
        'version': kv.get('version', 1),
        'labelmap': kv['labelmap'],
        'seats': seats,
        'votestrings': trimmed,
    }
    return human, data
