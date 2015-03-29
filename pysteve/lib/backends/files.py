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

from lib import constants

homedir = None

def init(config):
    global homedir
    homedir = config.get("general", "homedir")
    

def exists(election, *issue):
    "Returns True if an election/issue exists, False otherwise"
    elpath = os.path.join(homedir, "issues", election)
    if issue:
        elpath += "/" + issue[0] + ".json"
        return os.path.isfile(elpath)
    else:
        return os.path.isdir(elpath)


def getBasedata(election):
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
    basedata = getBasedata(election)
    if reopen:
        basedata['closed'] = False
    else:
        basedata['closed'] = True
    with open(elpath + "/basedata.json", "w") as f:
        f.write(json.dumps(basedata))
        f.close()


def getIssue(electionID, issueID):
    "Get JSON data from an issue"
    issuedata = None
    ihash = ""
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    if os.path.isfile(issuepath):        
        with open(issuepath, "r") as f:
            data = f.read()
            ihash = hashlib.sha224(data).hexdigest()
            f.close()
            issuedata = json.loads(data)

    return issuedata, ihash


def getVotes(electionID, issueID):
    "Read votes from the vote file"
    rvotes = getVotesRaw(electionID, issueID)
    votes = {}
    for key in rvotes:
        votes[key] = rvotes[key]['vote']
    return {}


def getVotesRaw(electionID, issueID):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            votes = json.loads(f.read())
            f.close()
            return votes
    return {}


def createElection(eid, basedata):
    elpath = os.path.join(homedir, "issues", eid)
    os.mkdir(elpath)
    with open(elpath  + "/basedata.json", "w") as f:
        f.write(json.dumps(basedata))
        f.close()
    with open(elpath  + "/voters.json", "w") as f:
        f.write("{}")
        f.close()


def updateElection(electionID, basedata):
    elpath = os.path.join(homedir, "issues", electionID)
    with open(elpath  + "/basedata.json", "w") as f:
        f.write(json.dumps(basedata))
        f.close()

def updateIssue(electionID, issueID, issueData):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    with open(issuepath, "w") as f:
        f.write(json.dumps(issueData))
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

def vote(electionID, issueID, uid, vote):
    "Casts a vote on an issue"
    votes = {}
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    if os.path.isfile(issuepath + ".votes"):
        with open(issuepath + ".votes", "r") as f:
            votes = json.loads(f.read())
            f.close()
    votes[uid] = {
        'vote': vote,
        'timestamp': time.time()
    }
    with open(issuepath + ".votes", "w") as f:
        f.write(json.dumps(votes))
        f.close()
    

def deleteIssue(electionID, issueID):
    "Deletes an issue if it exists"
    
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    if os.path.isfile(issuepath):
        os.unlink(issuepath)
    if os.path.isfile(issuepath + ".votes"):
        os.unlink(issuepath + ".votes")

def createIssue(electionID, issueID, data):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    with open(issuepath, "w") as f:
        f.write(json.dumps(data))
        f.close()

def voter_get(electionID, votekey):
    "Get vote UID/email with a given vote key hash"
    elpath = os.path.join(homedir, "issues", electionID)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
        for voter in voters:
            if voters[voter] == xhash:
                return voter
    return None

def voter_add(election, PID, xhash):
    elpath = os.path.join(homedir, "issues", election)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
    voters[PID] = xhash
    with open(elpath + "/voters.json", "w") as f:
        f.write(json.dumps(voters))
        f.close()

def voter_remove(election, UID):
    elpath = os.path.join(homedir, "issues", election)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
    if UID in voters:
        del voters[UID]
    with open(elpath + "/voters.json", "w") as f:
        f.write(json.dumps(voters))
        f.close()
        
def voter_has_voted(election, issue, uid):
    path = os.path.join(homedir, "issues", election, issue)
    votes = {}
    if os.path.isfile(path + ".json.votes"):
        with open(path + ".json.votes", "r") as f:
            votes = json.loads(f.read())
            f.close()
    return True if uid in votes else False

constants.appendBackend( {
    'id': 'file',
    'init': init,
    'document_exists': exists,
    'get_basedata': getBasedata,
    'election_close': close,
    'election_vote': vote,
    'election_list': listElections,
    'issue_list': listIssues,
    'election_create': createElection,
    'issue_create': createIssue,
    'issue_delete': deleteIssue,
    'election_update': updateElection,
    'issue_update': updateIssue,
    'issue_get': getIssue,
    'vote': vote,
    'votes_get': getVotes,
    'votes_get_raw': getVotesRaw,
    'voter_get_uid': voter_get,
    'voter_add': voter_add,
    'voter_remove': voter_remove,
    'voter_has_voted': voter_has_voted
})