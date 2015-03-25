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
""" STV Voting Plugin """
import re, json, random

from lib import constants

def validateSTV(vote, issue):
    "Tries to invalidate a vote, returns why if succeeded, None otherwise"
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(issue['candidates']))]
    for char in letters:
        if vote.count(char) > 1:
            return "Duplicate letters found"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def getproportion(votes, winners, step, surplus):
    """ Proportionally move votes
    :param votes:
    :param winners:
    :param step:
    :param surplus:
    :return:
    """
    prop = {}
    tvotes = 0
    for key in votes:
        vote = votes[key]
        xstep = step
        char = vote[xstep] if len(vote) > xstep else None
        # Step through votes till we find a non-winner vote
        while xstep < len(vote) and vote[xstep] in winners:
            xstep += 1
        if xstep >= step:
            tvotes += 1
        # We found it? Good, let's add that to the tally
        if xstep < len(vote) and not vote[xstep] in winners:
            char = vote[xstep]
            prop[char] = (prop[char] if char in prop else 0) + 1

    # If this isn't the initial 1st place tally, do the proportional math:
    # surplus votes / votes with an Nth preference * number of votes in that preference for the candidate
    if step > 0:
        for c in prop:
            prop[c] *= (surplus / tvotes) if surplus > 0 else 0
    return prop



def tallySTV(votes, issue):
    m = re.match(r"stv(\d+)", issue['type'])
    if not m:
        raise Exception("Not an STV vote!")
    
    numseats = int(m.group(1))
    candidates = []
    for c in issue['candidates']:
        candidates.append(c['name'])
    

    debug = []
    
    # Set up letters for mangling
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(candidates))]
    cc = "".join(letters)

    # Keep score of votes
    points = {}

    # Set all scores to 0 at first
    for c in cc:
        points[c] = 0

    # keep score of winners
    winners = []
    turn = 0

    # Find quota to win a seat
    quota = ( len(votes) / (numseats + 1) ) + 1
    debug.append("Seats available: %u. Votes cast: %u" % (numseats, len(votes)))
    debug.append("Votes required to win a seat: %u ( (%u/(%u+1))+1 )" % (quota, len(votes), numseats))

    
    surplus = 0
    # While we still have seats to fill
    if not len(candidates) < numseats:
        y = 0
        while len(winners) < numseats and len(cc) > 0 and turn < 1000:  #Don't run for > 1000 iterations, that's a bug
            turn += 1

            s = 0
            
            # Get votes
            xpoints = getproportion(votes, winners, 0, surplus)
            surplus = 0
            if turn == 1:
                debug.append("Initial tally: %s" % json.dumps(xpoints))
            else:
                debug.append("Proportional move: %s" % json.dumps(xpoints))
                
            for x in xpoints:
                points[x] += xpoints[x]
            mq = 0

            # For each candidate letter, find if someone won a seat
            for c in cc:
                if len(winners) >= numseats:
                    break
                if points[c] >= quota and not c in winners:
                    winners.append(c)
                    debug.append("WINNER: %s got elected in with %u votes! %u seats remain" % (c, points[c], numseats - len(winners)))
                    cc.replace(c, "")
                    mq += 1
                    surplus += points[c] - quota

            # If we found no winners in this round, eliminate the lowest scorer and retally
            if mq < 1:
                lowest = 99999999
                lowestC = None
                for c in cc:
                    if points[c] < lowest:
                        lowest = points[c]
                        lowestC = c

                debug.append("DRAW: %s is eliminated" % lowestC)
                if lowestC:
                    cc.replace(lowestC, "")
                else:
                    debug.append("No more canididates?? buggo?")
                    break
            y += 1

    # Everyone's a winner!!
    else:
        winners = letters

    # Compile list of winner names
    winnernames = []
    random.shuffle(winners)
    for c in winners:
        i = ord(c) - ord('a')
        winnernames.append(candidates[i])

    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winnernames,
        'debug': debug
    }


constants.VOTE_TYPES += (
    {
        'key': "stv1",
        'description': "Single Transferable Vote with 1 seat",
        'category': 'stv',
        'validate_func': validateSTV,
        'vote_func': None,
        'tally_func': tallySTV
    },
)

# Add ad nauseam
for i in range(2,constants.MAX_NUM+1):
    constants.VOTE_TYPES += (
        {
            'key': "stv%u" % i,
            'description': "Single Transferable Vote with %u seats" % i,
            'category': 'stv',
            'validate_func': validateSTV,
            'vote_func': None,
            'tally_func': tallySTV
        },
    )
