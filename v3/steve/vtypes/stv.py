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
    stv_tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stv_tool)

    return stv_tool


def tally(votestrings, kv):
    pass
