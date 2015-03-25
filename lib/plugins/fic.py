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
""" First in Class (FiC) Based Voting Plugin """
import re, heapq

from lib import constants

def validateFIC(vote, issue):
    "Tries to invalidate a vote, returns why if succeeded, None otherwise"
    m = re.match(r"fic(\d+)", issue['type'])
    if not m:
        return "Not an FiC vote!"
    numseats = int(m.group(1))
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(issue['candidates']))]
    if len(vote) > numseats:
        return "Vote contains too many candidates!"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def tallyFIC(votes, issue):
    m = re.match(r"fic(\d+)", issue['type'])
    if not m:
        raise Exception("Not an FiC vote!")
    
    numseats = int(m.group(1))
    candidates = []
    for c in issue['candidates']:
        candidates.append(c['name'])
    

    debug = []
    
    # Set up letters for mangling
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(candidates))]
    cc = "".join(letters)
    
    # Set up seats won
    winners = []
   
    # Set up vote matrix 
    matrix = {}
    for key in votes:
        vote = votes[key]
        i = 0
        for letter in vote:
            if not letter in matrix:
                matrix[letter] = 0
            matrix[letter] += numseats - i
            i += 1

    # Start counting
    winners = [l for l in matrix if matrix[l] in heapq.nlargest(numseats, matrix.values())]

    # Compile list of winner names
    winnernames = []
    x = 0
    for c in winners:
        i = ord(c) - ord('a')
        winnernames.append("%s ( %u)" % ( candidates[i], heapq.nlargest(numseats, matrix.values())[x]))
        x+=1

    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winnernames,
    }


constants.VOTE_TYPES += (
    {
        'key': "fic1",
        'description': "First in Class Votes with 1 point max",
        'category': 'fic',
        'validate_func': validateFIC,
        'vote_func': None,
        'tally_func': tallyFIC
    },
)

# Add ad nauseam
for i in range(2,constants.MAX_NUM+1):
    constants.VOTE_TYPES += (
        {
            'key': "fic%u" % i,
            'description': "First in Class Votes with %u points max" % i,
            'category': 'fic',
            'validate_func': validateFIC,
            'vote_func': None,
            'tally_func': tallyFIC
        },
    )