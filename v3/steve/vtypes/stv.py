#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ----
#
# ### TBD: DOCCO
#

import os.path
import importlib

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


def tally(votestrings, kv, names=None):
    "Run the STV tally process."

    # NOTE: the NAMES parameter is usually not passed, but is available
    # to compare operation against custom ordering of NAMES in the
    # LABELMAP. This function takes a specific approach, which differs
    # from historical orderings.

    # kv['labelmap'] should be: LABEL: NAME
    # for example: { 'a': 'John Doe', }
    labelmap = kv['labelmap']

    seats = kv['seats']

    # Remap all votestrings from a string sequence of label characters,
    # into a sequence of NAMEs.
    votes = [[labelmap[c] for c in v] for v in votestrings]

    # NOTE: it is important that the names are sorted, to create a
    # reproducible list of names. Callers may specify a custom ordering.
    if names is None:
        names = sorted(labelmap.values())
    results = stv_tool.run_stv(names, votes, seats)

    human = '\n'.join(
        f'{c.name:40}{" " if c.status == stv_tool.ELECTED else " not "}elected'
        for c in results.l
        )
    data = { 'raw': results, }
    return human, data
