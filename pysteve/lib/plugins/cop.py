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
Candidate or Party Voting Plugin
Currrently supports an arbitrary number of candidates from up to 26 parties
"""
import re, json, random

from lib import constants, form

def validateCOP(vote, issue):
    "Tries to invalidate a vote, returns why if succeeded, None otherwise"
    parties = {}
    for c in issue['candidates']:
        parties[c['pletter']] = True
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(parties))]
    ivote = -1
    try:
        ivote = int(vote)
    except:
        pass # This is a fast way to determine vote type, passing here is FINE!
    if not vote in letters and (ivote < 0 or ivote > len(issue['candidates'])):
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters,range(1,len(issue['candidates'])+1))
    return None

def parseCandidatesCOP(data):
    data = data if data else ""
    candidates = []
    pletter = ''
    cletter = ''
    pname = ''
    s = 0
    for line in data.split("\n"):
        line = line.strip()
        if len(line) > 0:
            arr = line.split(":", 1)
            letter = arr[0]
            letter = letter.lower()
            
            # Party delimiter?
            if letter in [chr(i) for i in range(ord('a'), ord('a') + 26)] and len(arr) > 1 and len(arr[1]) > 0:
                pname = arr[1]
                pletter = letter
            else:
                candidates.append({
                    'name': line,
                    'letter': str(s),
                    'pletter': pletter,
                    'pname': pname
                })
                s += 1
    return candidates


def tallyCOP(votes, issue):
    m = re.match(r"cop(\d+)", issue['type'])
    if not m:
        raise Exception("Not a COP vote!")
    
    numseats = int(m.group(1))
    parties = {}

    for c in issue['candidates']:
        if not c['pletter'] in parties:
            parties[c['pletter']] = {
                'name': c['pname'],
                'letter': c['pletter'],
                'surplus': 0,
                'candidates': []
            }
        parties[c['pletter']]['candidates'].append({
            'letter': c['letter'],
            'name': c['name'],
            'votes': 0,
            'elected': False
            })
    

    debug = []
    winners = []
    
        
    # Tally up all scores and surplus
    for key in votes:
        vote = votes[key]
        
        for party in parties:
            if parties[party]['letter'] == vote:
                parties[party]['surplus'] += 1
            else:
                for candidate in parties[party]['candidates']:
                    if candidate['letter'] == vote:
                        candidate['votes'] += 1
                
        
    numvotes = len(votes)
    
    if numseats < len(issue['candidates']):
        
        # Start by assigning all surplus (party votes) to the first listed candidate
        iterations = 0
        
        while numseats > len(winners) and iterations < 9999: # Catch forever-looping counts (in case of bug)
            quota = (numvotes / numseats * 1.0) # Make it a float to prevent from rounding down for now
            for party in parties:
                surplus = 0
                movedOn = False
                for candidate in parties[party]['candidates']:
                    if not candidate['elected'] and numseats > len(winners):
                        if candidate['votes'] >= quota:
                            candidate['elected'] = True
                            winners.append("%s (%s) %u" % ( candidate['name'], parties[party]['name'], candidate['votes']))
                            surplus += candidate['votes'] - quota
                    
                # If surplus of votes, add it to the next candidate in the same party
                if surplus > 0:
                    for candidate in parties[party]['candidates']:
                        if not candidate['elected']:
                            candidate['votes'] += surplus
                            movedOn = True
                            break
                        
                # If surplus but no candidates left, decrease the number of votes required by the surplus
                if not movedOn:
                    numvotes -= surplus
            
    # Everyone's a winner!!
    else:
        for party in parties:
            for candidate in parties[party]['candidates']:
                winners.append("%s (%s) %u" % ( candidate['name'], parties[party]['name'], candidate['votes']))
        

   
    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winners,
        'debug': debug
    }


constants.VOTE_TYPES += (
    {
        'key': "cop1",
        'description': "Candidate or Party Vote with 1 seat",
        'category': 'cop',
        'validate_func': validateCOP,
        'vote_func': None,
        'parsers': {
            'candidates': parseCandidatesCOP
        },
        'tally_func': tallyCOP
    },
)

# Add ad nauseam
for i in range(2,constants.MAX_NUM+1):
    constants.VOTE_TYPES += (
        {
            'key': "cop%02u" % i,
            'description': "Candidate or Party Vote with %u seats" % i,
            'category': 'cop',
            'validate_func': validateCOP,
            'vote_func': None,
            'parsers': {
                'candidates': parseCandidatesCOP
            },
            'tally_func': tallyCOP
        },
    )
