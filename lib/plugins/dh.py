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
""" D'Hondt (Jefferson) Based Voting Plugin """
import re, json, random

from lib import constants

def validateDH(vote, issue):
    "Tries to invalidate a vote, returns why if succeeded, None otherwise"
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(issue['candidates']))]
    if len(vote) > 1:
        return "Vote may only contain one letter!"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def tallyDH(votes, issue):
    m = re.match(r"dh(\d+)", issue['type'])
    if not m:
        raise Exception("Not a D'Hondt vote!")
    
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
    for vote in votes:
        matrix[vote] = [(matrix[vote] if vote in matrix else 0) + 1, 1]

    # Start counting
    while len(winners) < numseats:
        m = []
        for c in matrix:
            quotient = (matrix[c][1]/matrix[c][2])
            m.push(quotient)
        for c in matrix:
            quotient = (matrix[c][1]/matrix[c][2])
            if quotient == max(m):
                winners.append(c)
                matrix[c][2] += 1

    # Compile list of winner names
    winnernames = []
    for c in winners:
        i = ord(c) - ord('a')
        winnernames.append(candidates[i])

    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winnernames,
    }


constants.VOTE_TYPES += (
    {
        'key': "dh1",
        'description': "D'Hondt Election with 1 seat",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh2",
        'description': "D'Hondt Election with 2 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh3",
        'description': "D'Hondt Election with 3 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh4",
        'description': "D'Hondt Election with 4 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh5",
        'description': "D'Hondt Election with 5 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh6",
        'description': "D'Hondt Election with 6 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh7",
        'description': "D'Hondt Election with 7 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh8",
        'description': "D'Hondt Election with 8 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    },
    {
        'key': "dh9",
        'description': "D'Hondt Election with 9 seats",
        'category': 'dh',
        'validate_func': validateDH,
        'vote_func': None,
        'tally_func': tallyDH
    }
)