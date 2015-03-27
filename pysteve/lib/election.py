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


from __main__ import homedir, config

es = None

if config.get("database", "dbsys") == "elasticsearch":
    from elasticsearch import Elasticsearch
    es = Elasticsearch([
                    {
                        'host': config.get("elasticsearch", "host"),
                        'port': int(config.get("elasticsearch", "port")),
                        'url_prefix': config.get("elasticsearch", "uri"),
                        'use_ssl': False if config.get("elasticsearch", "secure") == "false" else True
                    },
                ])
    if not es.indices.exists("steve"):
        es.indices.create(index = "steve", body = {
                "settings": {
                    "number_of_shards" : 3,
                    "number_of_replicas" : 1
                }
            }
        )
    
import constants, voter
from plugins import *

def exists(election, *issue):
    "Returns True if an election/issue exists, False otherwise"
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        elpath = os.path.join(homedir, "issues", election)
        if issue:
            elpath += "/" + issue[0] + ".json"
            return os.path.isfile(elpath)
        else:
            return os.path.isdir(elpath)
    elif dbtype == "elasticsearch":
        s = "id:%s" % election
        doc = "elections"
        if issue and issue[0]:
            doc = "issues"
            s = "id:%s" % issue[0]
        res = es.search(index="steve", doc_type=doc, q = s, size = 1)
        if len(res['hits']['hits']) > 0:
            return True
        else:
            return False

def getBasedata(election, hideHash=False):
    "Get base data from an election"
    
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
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
    elif dbtype == "elasticsearch":
        res = es.search(index="steve", doc_type="elections", sort = "id", q = "id:%s" % election, size = 1)
        results = len(res['hits']['hits'])
        if results > 0:
            return res['hits']['hits'][0]['_source']
    return None

def close(election, reopen = False):
    "Mark an election as closed"
    dbtype = config.get("database", "dbsys")
    if exists(election):
        if dbtype == "file":
            elpath = os.path.join(homedir, "issues", election)
            basedata = getBasedata(election)
            if reopen:
                basedata['closed'] = False
            else:
                basedata['closed'] = True
            with open(elpath + "/basedata.json", "w") as f:
                f.write(json.dumps(basedata))
                f.close()
    elif dbtype == "elasticsearch":
        basedata = getBasedata(election)
        if reopen:
            basedata['closed'] = False
        else:
            basedata['closed'] = True
        es.index(index="steve", doc_type="elections", id=election, body = basedata )
        

def getIssue(electionID, issueID):
    "Get JSON data from an issue"
    issuedata = None
    ihash = ""
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath):
            
            with open(issuepath, "r") as f:
                data = f.read()
                ihash = hashlib.sha224(data).hexdigest()
                f.close()
                issuedata = json.loads(data)
    elif dbtype == "elasticsearch":
        res = es.search(index="steve", doc_type="issues", q = "id:%s" % issueID, size = 1)
        results = len(res['hits']['hits'])
        if results > 0:
            issuedata = res['hits']['hits'][0]['_source']
            ihash = hashlib.sha224(json.dumps(issuedata)).hexdigest()
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
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
        issuedata = {}
        if os.path.isfile(issuepath):
            with open(issuepath, "r") as f:
                data = f.read()
                f.close()
                issuedata = json.loads(data)
        return issuedata
    elif dbtype == "elasticsearch":
        res = es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = {}
            for entry in res['hits']['hits']:
                votes[entry['_source']['key']] = entry['_source']['data']['vote']
            return votes
    return {}



def getVotesRaw(electionID, issueID):
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json.votes"
        if os.path.isfile(issuepath):
            with open(issuepath, "r") as f:
                votes = json.loads(f.read())
                f.close()
                return votes
    elif dbtype == "elasticsearch":
        res = es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = {}
            for entry in res['hits']['hits']:
                votes[entry['_source']['key']] = entry['_source']['data']
            return votes
    return {}


def createElection(eid, title, owner, monitors, starts, ends, isopen):
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
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
    elif dbtype == "elasticsearch":
        es.index(index="steve", doc_type="elections", id=eid, body =
            {
                'id': eid,
                'title': title,
                'owner': owner,
                'monitors': monitors,
                'starts': starts,
                'ends': ends,
                'hash': hashlib.sha512("%f-stv-%s" % (time.time(), os.environ['REMOTE_ADDR'] if 'REMOTE_ADDR' in os.environ else random.randint(1,99999999999))).hexdigest(),
                'open': isopen
            }
        );


def listIssues(election):
    "List all issues in an election"
    issues = []
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        elpath = os.path.join(homedir, "issues", election)
        if os.path.isdir(elpath):
            issues = [f.strip(".json") for f in os.listdir(elpath) if os.path.isfile(os.path.join(elpath, f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
    elif dbtype == "elasticsearch":
        try:
            res = es.search(index="steve", doc_type="issues", sort = "id", q = "election:%s" % election, size = 999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    issues.append(entry['_source']['id'])
        except:
            pass # THIS IS OKAY! ES WILL FAIL IF THERE ARE NO ISSUES YET
    return issues

def listElections():
    "List all elections"
    elections = []
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        path = os.path.join(homedir, "issues")
        if os.path.isdir(path):
            elections = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    elif dbtype == "elasticsearch":
        try:
            res = es.search(index="steve", doc_type="elections", sort = "id", q = "*", size = 99999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    source  = entry['_source']
                    elections.append(source['id'])
        except Exception as err:
            pass # THIS IS OKAY! On initial setup, this WILL fail until an election has been created
    return elections

def getVoteType(issue):
    for voteType in constants.VOTE_TYPES:
        if voteType['key'] == issue['type']:
            return voteType
    return {}

def vote(electionID, issueID, voterID, vote):
    "Casts a vote on an issue"
    votes = {}
    basedata = getBasedata(electionID)
    issueData = getIssue(electionID, issueID)
    if basedata and issueData:
        votehash = hashlib.sha224(basedata['hash'] + issueID + voterID + vote).hexdigest()
        
        # Vote verification
        voteType = getVoteType(issueData)
        if voteType.get('vote_func'):
            # This will/should raise an exception if the vote is invalid
            voteType['vote_func'](basedata, issueID, voterID, vote)
            
        dbtype = config.get("database", "dbsys")
        if dbtype == "file":
            issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
            if os.path.isfile(issuepath + ".votes"):
                with open(issuepath + ".votes", "r") as f:
                    votes = json.loads(f.read())
                    f.close()
            votes[voterID] = {
                'vote': vote,
                'timestamp': time.time()
            }
            with open(issuepath + ".votes", "w") as f:
                f.write(json.dumps(votes))
                f.close()
        
            # LURK on who voted :O :O :O
            if config.has_option("general", "lurk") and config.get("general", "lurk") == "yes":
                email = voter.get(electionID, basedata, voterID)
                lurks = {}
                lurkpath = os.path.join(homedir, "issues", electionID, "who.voted")
                if os.path.isfile(lurkpath):
                    with open(lurkpath, "r") as f:
                        lurks = json.loads(f.read())
                        f.close()
                lurks[email] = True
                with open(lurkpath, "w") as f:
                    f.write(json.dumps(lurks))
                    f.close()
        elif dbtype == "elasticsearch":
            es.index(index="steve", doc_type="votes", id=votehash, body =
                {
                    'issue': issueID,
                    'election': electionID,
                    'key': votehash,
                    'data': {
                        'timestamp': time.time(),
                        'vote': vote
                    }
                }
            );
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
    
    if exists(electionID):
        dbtype = config.get("database", "dbsys")
        if dbtype == "file":
            issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
            if os.path.isfile(issuepath):
                os.unlink(issuepath)
            if os.path.isfile(issuepath + ".votes"):
                os.unlink(issuepath + ".votes")
        elif dbtype == "elasticsearch":
            es.delete(index="steve", doc_type="votes", id=votehash);
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
    output.append("\nYou can monitor votes and recasts online at: %s/monitor.html?%s" % (config.get("general", "rooturl"), electionID))
    return tothash, "\n".join(output)

def createIssue(electionID, issueID, data):
    if not exists(electionID, issueID):
        dbtype = config.get("database", "dbsys")
        if dbtype == "file":
            issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
            with open(issuepath, "w") as f:
                f.write(json.dumps(data))
                f.close()
        elif dbtype == "elasticsearch":
            data['election'] = electionID
            data['id'] = issueID
            es.index(index="steve", doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = data);
    else:
        raise Exception("Issue already exists!")