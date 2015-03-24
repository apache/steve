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
import random
import time

from __main__ import homedir, config

import constants
from plugins import *

def exists(election, *issue):
    "Returns True if an election/issue exists, False otherwise"
    elpath = os.path.join(homedir, "issues", election)
    if issue:
        elpath += "/" + issue[0] + ".json"
        return os.path.isfile(elpath)
    else:
        return os.path.isdir(elpath)


def getBasedata(election, hideHash=False):
    "Get base data from an election"
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

def close(election, reopen = False):
    "Mark an election as closed"
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        basedata = {}
        with open(elpath + "/basedata.json", "r") as f:
            data = f.read()
            f.close()
            basedata = json.loads(data)
        if reopen:
            basedata['closed'] = False
        else:
            basedata['closed'] = True
        with open(elpath + "/basedata.json", "w") as f:
            f.write(json.dumps(basedata))
            f.close()

def getIssue(electionID, issueID):
    "Get JSON data from an issue"
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    issuedata = None
    if os.path.isfile(issuepath):
        ihash = ""
        with open(issuepath, "r") as f:
            data = f.read()
            ihash = hashlib.sha224(data).hexdigest()
            f.close()
            issuedata = json.loads(data)
        issuedata['hash'] = ihash
        issuedata['id'] = issueID
        issuedata['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
        issuedata['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
        
        # Add vote category for JS magic
        for vtype in constants.VOTE_TYPES:
            if vtype['key'] == issuedata['type']:
                issuedata['category'] = vtype['category']
                break
            
    return issuedata


def getVotes(electionID, issueID):
    "Read votes from the vote file"
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
    issuedata = {}
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            data = f.read()
            f.close()
            issuedata = json.loads(data)
    return issuedata

def createElection(eid, title, owner, monitors, starts, ends, isopen):
    elpath = os.path.join(homedir, "issues", eid)
    os.mkdir(elpath)
    with open(elpath  + "/basedata.json", "w") as f:
        f.write(json.dumps({
            'title': title,
            'owner': owner,
            'monitors': monitors,
            'starts': starts,
            'ends': ends,
            'hash': hashlib.sha512("%f-stv-%s" % (time.time(), os.environ['REMOTE_ADDR'] if 'REMOTE_ADDR' in os.environ else random.randint(1,99999999999))).hexdigest(),
            'open': isopen
        }))
        f.close()
    with open(elpath  + "/voters.json", "w") as f:
        f.write("{}")
        f.close()


def listIssues(election):
    "List all issues in an election"
    issues = []
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        issues = [f.strip(".json") for f in os.listdir(elpath) if os.path.isfile(os.path.join(elpath, f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
    return issues

def listElections():
    "List all elections"
    elections = []
    path = os.path.join(homedir, "issues")
    if os.path.isdir(path):
        elections = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    return elections

def vote(electionID, issueID, voterID, vote):
    "Casts a vote on an issue"
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

def getVotes(electionID, issueID):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            votes = json.loads(f.read())
            f.close()
            return votes
    else:
        return {}
    
def validType(issueType):
    for voteType in constants.VOTE_TYPES:
        if voteType['key'] == issueType:
            return True
    return False

def invalidate(issueData, vote):
    for voteType in constants.VOTE_TYPES:
        if voteType['key'] == issueData['type']:
            return voteType['validate_func'](vote, issueData)
    return "Invalid vote type!"

def tally(votes, issue):
    for voteType in constants.VOTE_TYPES:
        if voteType['key'] == issue['type']:
            return voteType['tally_func'](votes, issue)
    raise Exception("Invalid vote type!")

def deleteIssue(electionID, issueID):
    "Deletes an issue if it exists"
    if exists(electionID):
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath):
            os.unlink(issuepath)
        if os.path.isfile(issuepath + ".votes"):
            os.unlink(issuepath + ".votes")
        return True
    else:
        raise Exception("No such election")


def getHash(electionID):
    basedata = getBasedata(electionID)
    issues = listIssues(electionID)
    ihash = ""
    output = []
    for issue in issues:
        issuedata = getIssue(electionID, issue)
        votes = getVotes(electionID, issue)
        ihash += issuedata['hash']
        output.append("Issue #%s: %s\n- Checksum: %s\n- Votes cast: %u\n" % (issue, issuedata['title'], issuedata['hash'], len(votes)))
    tothash = hashlib.sha224(ihash).hexdigest()
    output.insert(0, ("You are receiving this data because you are listed as a monitor for this election.\nThe following data shows the state of the election data on disk. If any of these checksums change, especially the main checksum, then the election has been edited (rigged?) after invites were sent out.\n\nMain Election Checksum : %s\n\n" % tothash))
    return tothash, "\n".join(output)
