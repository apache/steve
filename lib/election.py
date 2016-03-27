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
from itertools import izip

try:
    from __main__ import config
except:
    import ConfigParser as configparser
    config = configparser.RawConfigParser()
    config.read("%s/../../../steve.cfg" % (os.path.dirname(__file__)))
    
import constants, voter
from plugins import *
from backends import *



# Set up DB backend
backend = constants.initBackend(config)


def exists(election, *issue):
    "Returns True if an election/issue exists, False otherwise"
    return backend.document_exists(election, *issue)

def getBasedata(election, hideHash=False):
    "Get base data from an election"
    return backend.get_basedata(election)

def close(election, reopen = False):
    "Mark an election as closed"
    backend.close(election, reopen)
    

def getIssue(electionID, issueID):
    "Get JSON data from an issue"
    issuedata, ihash = backend.issue_get(electionID, issueID)
    if issuedata:
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
    return backend.votes_get(electionID, issueID)

def getVotesRaw(electionID, issueID):
    return backend.votes_get_raw(electionID, issueID)

def getVoteHistory(electionID, issueID):
    return backend.vote_history(electionID, issueID)


def createElection(eid, title, owner, monitors, starts, ends, isopen):
    basedata =  {
            'id': eid,
            'title': title,
            'owner': owner,
            'monitors': monitors,
            'starts': starts,
            'ends': ends,
            'hash': hashlib.sha512("%f-stv-%s" % (time.time(), os.environ['REMOTE_ADDR'] if 'REMOTE_ADDR' in os.environ else random.randint(1,99999999999))).hexdigest(),
            'open': isopen
        }
    backend.election_create(eid, basedata)
    

def updateElection(electionID, basedata):
    backend.election_update(electionID, basedata)


def updateIssue(electionID, issueID, issueData):
    backend.issue_update(electionID, issueID, issueData)


def listIssues(election):
    "List all issues in an election"
    return backend.issue_list(election)

def listElections():
    "List all elections"
    return backend.election_list()


def getVoteType(issue):
    for voteType in constants.VOTE_TYPES:
        if voteType['key'] == issue['type']:
            return voteType
    return None

def vote(electionID, issueID, voterID, vote):
    "Casts a vote on an issue"
    basedata = getBasedata(electionID)
    issueData = getIssue(electionID, issueID)
    if basedata and issueData:
        xhash = hashlib.sha224(election + ":" + voterID).hexdigest()
        vhash = hashlib.sha224(xhash + issueID).hexdigest()
        votehash = hashlib.sha224(basedata['hash'] + issueID + voterID + vote).hexdigest()
        
        # Vote verification
        voteType = getVoteType(issueData)
        if voteType.get('vote_func'):
            # This will/should raise an exception if the vote is invalid
            uid = voter.get(electionID, basedata, voterID)
            voteType['vote_func'](basedata, issueID, voterID, vote, uid)
            
        backend.vote(electionID, issueID, voterID, vote, vhash = vhash)
        
        # LURK on who voted :O :O :O
       # if config.has_option("general", "lurk") and config.get("general", "lurk") == "yes":
            #email = voter.get(electionID, basedata, voterID)
          #  backend['lurk'](electionID, email)
       
        return votehash
    else:
        raise Exception("No such election")

    
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
    
    if exists(electionID, issueID):
        backend.issue_delete(electionID, issueID)
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
    output.append("\nYou can monitor votes and recasts online at: %s/monitor.html?%s" % (config.get("general", "rooturl"), electionID))
    return tothash, "\n".join(output)

def createIssue(electionID, issueID, data):
    backend.issue_create(electionID, issueID, data)