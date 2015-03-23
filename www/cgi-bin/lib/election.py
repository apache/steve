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
import hashlib
import json
import os

from __main__ import homedir, config


def exists(election):
    elpath = os.path.join(homedir, "issues", election)
    return os.path.isdir(elpath)


def getBasedata(election, hideHash=False):
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        with open(elpath + "/basedata.json", "r") as f:
            data = f.read()
            f.close()
            basedata = json.loads(data)
            if hideHash and 'hash' in basedata:
                del basedata['hash']
            basedata['id'] = election
            return basedata
    return None


def getIssue(electionID, issueID):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    issuedata = None
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            data = f.read()
            f.close()
            issuedata = json.loads(data)
        issuedata['id'] = issueID
        issuedata['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
        issuedata['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
    return issuedata


def getVotes(electionID, issueID):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
    issuedata = {}
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            data = f.read()
            f.close()
            issuedata = json.loads(data)
    return issuedata


def listIssues(election):
    issues = []
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        issues = [f.strip(".json") for f in os.listdir(elpath) if os.path.isfile(os.path.join(elpath, f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
    return issues


def vote(electionID, issueID, voterID, vote):
    votes = {}
    basedata = getBasedata(electionID)
    if basedata:
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath + ".votes"):
            with open(issuepath + ".votes", "r") as f:
                votes = json.loads(f.read())
                f.close()
        votes[voterID] = vote
        with open(issuepath + ".votes", "w") as f:
            f.write(json.dumps(votes))
            f.close()
        votehash = hashlib.sha224(basedata['hash'] + issueID + voterID + vote).hexdigest()
        return votehash
    else:
        raise Exception("No such election")


def invalidate(issueData, vote):
    letters = ['y', 'n', 'a']
    if issueData['type'].find("stv") == 0:
        letters = [chr(i) for i in range(ord('a'), ord('a') + len(issueData['candidates']))]
    for char in letters:
        if vote.count(char) > 1:
            return "Duplicate letters found"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def deleteIssue(electionID, issueID):
    if exists(electionID):
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath):
            os.unlink(issuepath)
        if os.path.isfile(issuepath + ".votes"):
            os.unlink(issuepath + ".votes")
        return True
    else:
        raise Exception("No such election")


debug = []


def yna(votes):
    y = n = a = 0
    for vote in votes.values():
        if vote == 'y':
            y += 1
        if vote == 'n':
            n += 1
        if vote == 'a':
            a += 1

    return y, n, a


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
        char = vote[xstep]
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
            prop[c] *= surplus / tvotes

    debug.append("Proportional move: %s" % json.dumps(prop))
    return prop


def stv(candidates, votes, numseats):
    """ Calculate N winners using STV
    :param candidates:
    :param votes:
    :param int numseats: the number of seats available
    :return:
    """

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
    debug.append("Votes required to win a seat: %u" % quota)

    # While we still have seats to fill
    if not len(candidates) < numseats:
        while len(winners) < numseats and len(cc) > 0 and turn < 1000:  #Don't run for > 1000 iterations, that's a bug
            turn += 1

            s = 0
            y = 0
            # Get votes
            xpoints = getproportion(votes, winners, y, 0)
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

    # Everyone's a winner!!
    else:
        winners = letters

    # Compile list of winner names
    winnernames = []
    for c in winners:
        i = ord(c) - ord('a')
        winnernames.append(candidates[i]['name'])

    # Return the data
    return winners, winnernames, debug