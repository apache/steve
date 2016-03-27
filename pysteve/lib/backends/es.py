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

class ElasticSearchBackend:
    es = None
    
    def __init__(self, config):
        " Init - get config and turn it into an ES instance"
        from elasticsearch import Elasticsearch
        self.es = Elasticsearch([
                        {
                            'host': config.get("elasticsearch", "host"),
                            'port': int(config.get("elasticsearch", "port")),
                            'url_prefix': config.get("elasticsearch", "uri"),
                            'use_ssl': False if config.get("elasticsearch", "secure") == "false" else True
                        },
                    ])
        
        # Check that we have a 'steve' index. If not, create it.
        if not self.es.indices.exists("steve"):
            self.es.indices.create(index = "steve", body = {
                    "settings": {
                        "number_of_shards" : 3,
                        "number_of_replicas" : 1
                    }
                }
            )
        
    
    
    def document_exists(self, election, *issue):
        "Does this election or issue exist?"
        doc = "elections"
        eid = election
        if issue and issue[0]:
            doc = "issues"
            eid = hashlib.sha224(election + "/" + issue[0]).hexdigest()
        return self.es.exists(index="steve", doc_type=doc, id=eid)
        
        
    
    def get_basedata(self, election):
        "Get base data from an election"
        res = self.es.get(index="steve", doc_type="elections", id=election)
        if res:
            return res['_source']
        return None
    
    
    def close(self, election, reopen = False):
        "Mark an election as closed"
        basedata = self.get_basedata(election)
        if reopen == True:
            basedata['closed'] = False
        else:
            basedata['closed'] = True
        self.es.index(index="steve", doc_type="elections", id=election, body = basedata )
            
    
    def issue_get(self, electionID, issueID):
        "Get JSON data from an issue"
        issuedata = None
        ihash = ""
        iid = hashlib.sha224(electionID + "/" + issueID).hexdigest()
        res = self.es.get(index="steve", doc_type="issues", id=iid)
        if res:
            issuedata = res['_source']
            ihash = hashlib.sha224(json.dumps(issuedata)).hexdigest()
        return issuedata, ihash
    
    
    def votes_get(self, electionID, issueID):
        "Read votes and return as a dict"
        res = self.es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = {}
            for entry in res['hits']['hits']:
                votes[entry['_source']['key']] = entry['_source']['data']['vote']
            return votes
        return {}
    
    
    
    def votes_get_raw(self, electionID, issueID):
        "Read votes and return raw format"
        res = self.es.search(index="steve", doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = []
            for entry in res['hits']['hits']:
                votes.append(entry['_source'])
            return votes
        return {}
    
    def vote_history(self, electionID, issueID):
        "Read vote history and return raw format"
        res = self.es.search(index="steve", doc_type="vote_history", sort = "data.timestamp", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = []
            for entry in res['hits']['hits']:
                votes.append(entry['_source'])
            return votes
        return []
    
    def election_create(self,electionID, basedata):
        "Create a new election"
        self.es.index(index="steve", doc_type="elections", id=electionID, body =
            basedata
        );
    
    def election_update(self,electionID, basedata):
        "Update an election with new data"
        self.es.index(index = "steve", doc_type = "elections", id=electionID, body = basedata)
    
    
    def issue_update(self,electionID, issueID, issueData):
        "Update an issue with new data"
        self.es.index(index = "steve", doc_type = "issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = issueData)
    
    
    def issue_list(self, election):
        "List all issues in an election"
        issues = []
        try:
            res = self.es.search(index="steve", doc_type="issues", sort = "id", q = "election:%s" % election, size = 999, _source_include = 'id')
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    issues.append(entry['_source']['id'])
        except:
            pass # THIS IS OKAY! ES WILL FAIL IF THERE ARE NO ISSUES YET
        return issues
    
    def election_list(self):
        "List all elections"
        elections = []
        try:
            res = self.es.search(index="steve", doc_type="elections", sort = "id", q = "*", size = 9999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    source  = entry['_source']
                    elections.append(source['id'])
        except Exception as err:
            pass # THIS IS OKAY! On initial setup, this WILL fail until an election has been created
        return elections
    
    def vote(self,electionID, issueID, uid, vote):
        "Casts a vote on an issue"
        eid = hashlib.sha224(electionID + ":" + issueID + ":" + uid).hexdigest()
        now = time.time()
        self.es.index(index="steve", doc_type="votes", id=eid, body =
            {
                'issue': issueID,
                'election': electionID,
                'key': uid,
                'data': {
                    'timestamp': now,
                    'vote': vote
                }
            }
        );
        # Backlog of changesets
        self.es.index(index="steve", doc_type="vote_history", body =
            {
                'issue': issueID,
                'election': electionID,
                'key': uid,
                'data': {
                    'timestamp': now,
                    'vote': vote
                }
            }
        );
        
        
    def issue_delete(self, electionID, issueID):
        "Deletes an issue if it exists"
        self.es.delete(index="steve", doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest());
        
    def issue_create(self,electionID, issueID, data):
        "Create an issue"
        self.es.index(index="steve", doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = data);
    
    
    
    def voter_get_uid(self, electionID, votekey):
        "Get the UID/email for a voter given the vote key hash"
        try:
            res = self.es.search(index="steve", doc_type="voters", q = "election:%s" % electionID, size = 9999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    voter = entry['_source']
                    if voter['hash'] == votekey:
                        return voter['uid']
        except:
            return False # ES Error, probably not seeded the voters doc yet
    
    def voter_add(self,election, PID, xhash):
        "Add a voter to the DB"
        eid = hashlib.sha224(election + ":" + PID).hexdigest()
        self.es.index(index="steve", doc_type="voters", id=eid, body = {
            'election': election,
            'hash': xhash,
            'uid': PID
            }
        )
        
    def ballot_scrub(self,election, xhash, uid = None):
        "Scrub a ballot"
        if uid:
            xhash = hashlib.sha224(election + ":" + uid).hexdigest()
            
        # Find ballots and votes matching
        res = self.es.search(index="steve", doc_type="votes", body = {
            "query": {
                "match": {
                    "key": xhash
                }
            }
        }, size = 999)
        results = len(res['hits']['hits'])
        if results > 0:
            for entry in res['hits']['hits']:
                self.es.delete(index="steve", doc_type="votes", id=entry['_id']);
        
    def voter_remove(self,election, UID):
        "Remove the voter with the given UID"
        votehash = hashlib.sha224(election + ":" + UID).hexdigest()
        self.es.delete(index="steve", doc_type="voters", id=votehash);
    
    def voter_has_voted(self,election, issue, uid):
        "Return true if the voter has voted on this issue, otherwise false"
        eid = hashlib.sha224(election + ":" + issue + ":" + uid).hexdigest()
        try:
            return self.es.exists(index="steve", doc_type="votes", id=eid)
        except:
            return False

    def voter_ballots(self, UID):
        """Find all elections (and ballots) this user has participated in"""
        
        # First, get all elections
        elections = {}
        
        res = self.es.search(index="steve", doc_type="elections", sort = "id", q = "*", size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            for entry in res['hits']['hits']:
                election  = entry['_source']
                # Mark election open or closed
                elections[election['id']] = {
                    'title': election['title'],
                    'open': False if election['closed'] else True
                }
                
        # Then, get all ballots and note whether they still apply or not
        ballots = {}
        res = self.es.search(index="steve", doc_type="voters", body = {
            "query": {
                "match": {
                    "uid": UID
                }
            }
        }, size = 999)
        results = len(res['hits']['hits'])
        if results > 0:
            for entry in res['hits']['hits']:
                ballot = entry['_source']
                ballots[ballot['election']] = {
                    'ballot': entry['_id'],
                    'metadata': elections[ballot['election']]
                }
        return ballots
        
constants.appendBackend("elasticsearch", ElasticSearchBackend)