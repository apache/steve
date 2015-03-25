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
"""
CORE VOTE PLUGINS:

    yna:    Yes/No/Abstain
    stv:    Single Transferable Vote
    dh:     D'Hondt (Jefferson) Voting
    fpp:    First Past the Post (Presidential elections)
    mntv:   Multiple Non-Transferable Votes
    cop:    Candidate or Party Voting
    fic:    First in Class Voting
"""

__all__ = ['yna','stv','dh','fpp','mntv','cop','fic']