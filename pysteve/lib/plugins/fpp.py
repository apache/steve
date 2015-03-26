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
""" FPP (First Past the Post) Based Voting Plugin """
import re, json

from lib import constants

def validateFPP(vote, issue):
    "Tries to validate a vote, returns why if not valid, None otherwise"
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(issue['candidates']))]
    if len(vote) > 1:
        return "Vote may only contain one letter!"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def tallyFPP(votes, issue):
    candidates = []
    for c in issue['candidates']:
        candidates.append(c['name'])
    

    debug = []
    matrix = {}
    
    # Set up counting matrix
    for key in votes:
        vote = votes[key]
        matrix[vote] = (matrix[vote] if vote in matrix else 0) + 1
    
    l = []
    for x in matrix:
        l.append(matrix[x])
        
    cc = []
    for x in matrix:
        if matrix[x] == max(l):
            cc.append(x)
    winners = []
    winnernames = []
    
    for c in cc:
        i = ord(c) - ord('a')
        winners.append(c)
        winnernames.append(candidates[i])


    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winnernames,
        'winnerpct': ((1.00*max(l)/len(votes))*100) if len(votes) > 0 else 0.00,
        'tie': True if len(winners) > 1 else False
    }


constants.appendVote (
    {
        'key': "fpp",
        'description': "First Past the Post (FPP) Election",
        'category': 'fpp',
        'validate_func': validateFPP,
        'vote_func': None,
        'tally_func': tallyFPP
    },
)
