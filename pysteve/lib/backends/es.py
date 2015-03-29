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

es = None

def init(config):
    global es
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
    


def exists(election, *issue):
    doc = "elections"
    eid = election
    if issue and issue[0]:
        doc = "issues"
        eid = hashlib.sha224(election + "/" + issue[0]).hexdigest()
    return es.exists(index="steve", doc_type=doc, id=eid)
    
    

def getBasedata(election):
    "Get base data from an election"
    res = es.get(index="steve", doc_type="elections", id=election)
    if res:
        return res['_source']
    return None


def close(election, reopen = False):
    "Mark an election as closed"
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
    iid = hashlib.sha224(electionID + "/" + issueID).hexdigest()
    res = es.get(index="steve", doc_type="issues", id=iid)
    if res:
        issuedata = res['_source']
        ihash = hashlib.sha224(json.dumps(issuedata)).hexdigest()
    return issuedata, ihash


def getVotes(electionID, issueID):
    "Read votes from the vote file"
    res = es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999999)
    results = len(res['hits']['hits'])
    if results > 0:
        votes = {}
        for entry in res['hits']['hits']:
            votes[entry['_source']['key']] = entry['_source']['data']['vote']
        return votes
    return {}



def getVotesRaw(electionID, issueID):
    res = es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999999)
    results = len(res['hits']['hits'])
    if results > 0:
        votes = {}
        for entry in res['hits']['hits']:
            votes[entry['_source']['key']] = entry['_source']['data']
        return votes
    return {}


def createElection(electionID, basedata):
    "Create a new election"
    es.index(index="steve", doc_type="elections", id=electionID, body =
        basedata
    );

def updateElection(electionID, basedata):
    es.index(index = "steve", doc_type = "elections", id=electionID, body = basedata)

def updateIssue(electionID, issueID, issueData):
    es.index(index = "steve", doc_type = "issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = issueData)


def listIssues(election):
    "List all issues in an election"
    issues = []
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

def vote(electionID, issueID, uid, vote):
    "Casts a vote on an issue"
    eid = hashlib.sha224(electionID + ":" + issueID + ":" + uid).hexdigest()
    es.index(index="steve", doc_type="votes", id=eid, body =
        {
            'issue': issueID,
            'election': electionID,
            'key': uid,
            'data': {
                'timestamp': time.time(),
                'vote': vote
            }
        }
    );
    
    
def deleteIssue(electionID, issueID):
    "Deletes an issue if it exists"
    es.delete(index="steve", doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest());
    
def createIssue(electionID, issueID, data):
    es.index(index="steve", doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = data);



def voter_get(electionID, votekey):
    "Get the UID/email for a voter given the vote key hash"
    try:
        res = es.search(index="steve", doc_type="voters", q = "election:%s" % electionID, size = 999999)
        results = len(res['hits']['hits'])
        if results > 0:
            for entry in res['hits']['hits']:
                voter = entry['_source']
                if voter['hash'] == votekey:
                    return voter['uid']
    except:
        return False # ES Error, probably not seeded the voters doc yet

def voter_add(election, PID, xhash):
    eid = hashlib.sha224(election + ":" + PID).hexdigest()
    es.index(index="steve", doc_type="voters", id=eid, body = {
        'election': election,
        'hash': xhash,
        'uid': PID
        }
    )
    
def voter_remove(election, UID):
    votehash = hashlib.sha224(election + ":" + UID).hexdigest()
    es.delete(index="steve", doc_type="voters", id=votehash);

def voter_has_voted(election, issue, uid):
    eid = hashlib.sha224(election + ":" + issue + ":" + uid).hexdigest()
    try:
        return es.exists(index="steve", doc_type="votes", id=eid)
    except:
        return False

constants.appendBackend( {
    'id': 'elasticsearch',
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