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
import elasticsearch


class SteveESWrapper(object):
    """
       Class for rewriting old-style queries to the new ones,
       where doc_type is an integral part of the DB name
    """
    def __init__(self, ES):
        self.ES = ES
    
    def get(self, index, doc_type, id):
        return self.ES.get(index = index+'_'+doc_type, doc_type = '_doc', id = id)
    def exists(self, index, doc_type, id):
        return self.ES.exists(index = index+'_'+doc_type, doc_type = '_doc', id = id)
    def delete(self, index, doc_type, id):
        return self.ES.delete(index = index+'_'+doc_type, doc_type = '_doc', id = id)
    def index(self, index, doc_type, id = None, body = None):
        return self.ES.index(index = index+'_'+doc_type, doc_type = '_doc', id = id, body = body)
    def update(self, index, doc_type, id, body):
        return self.ES.update(index = index+'_'+doc_type, doc_type = '_doc', id = id, body = body)
    def scroll(self, scroll_id, scroll):
        return self.ES.scroll(scroll_id = scroll_id, scroll = scroll)
    def delete_by_query(self, **kwargs):
        return self.ES.delete_by_query(**kwargs)
    def search(self, index, doc_type, size = 100, scroll = None, _source_include = None, body = None, q = None, sort = None):
        if q:
            body = {
                "query": {
                    "query_string": {
                        "query": q
                    }
                }
            }
        if sort and body:
            if '.keyword' not in sort:
                sort = sort + ".keyword"
            body['sort'] = [
                { sort: 'asc'}
            ]
        return self.ES.search(
            index = index+'_'+doc_type,
            doc_type = '_doc',
            size = size,
            scroll = scroll,
            _source_include = _source_include,
            body = body
            )
    def count(self, index, doc_type = '*', body = None):
        return self.ES.count(
            index = index+'_'+doc_type,
            doc_type = '_doc',
            body = body
            )

class SteveESWrapperSeven(object):
    """
       Class for rewriting old-style queries to the >= 7.x ones,
       where doc_type is an integral part of the DB name and NO DOC_TYPE!
    """
    def __init__(self, ES):
        self.ES = ES
    
    def get(self, index, doc_type, id):
        return self.ES.get(index = index+'_'+doc_type, id = id)
    def exists(self, index, doc_type, id):
        return self.ES.exists(index = index+'_'+doc_type, id = id)
    def delete(self, index, doc_type, id):
        return self.ES.delete(index = index+'_'+doc_type, id = id)
    def index(self, index, doc_type, id = None, body = None):
        return self.ES.index(index = index+'_'+doc_type, id = id, body = body)
    def update(self, index, doc_type, id, body):
        return self.ES.update(index = index+'_'+doc_type, id = id, body = body)
    def scroll(self, scroll_id, scroll):
        return self.ES.scroll(scroll_id = scroll_id, scroll = scroll)
    def delete_by_query(self, **kwargs):
        return self.ES.delete_by_query(**kwargs)
    def search(self, index, doc_type, size = 100, scroll = None, _source_include = None, body = None, q = None, sort = None):
        if q:
            body = {
                "query": {
                    "query_string": {
                        "query": q
                    }
                }
            }
        if sort and body:
            if '.keyword' not in sort:
                sort = sort + ".keyword"
            body['sort'] = [
                { sort: 'asc'}
            ]
        return self.ES.search(
            index = index+'_'+doc_type,
            size = size,
            scroll = scroll,
            _source_includes = _source_include,
            body = body
            )
    def count(self, index, doc_type = '*', body = None):
        return self.ES.count(
            index = index+'_'+doc_type,
            body = body
            )
    

class SteveDatabase(object):
    def __init__(self, config):
        self.config = config
        self.dbname = config.get('elasticsearch','index')
        self.ES = elasticsearch.Elasticsearch([{
                'host': config.get('elasticsearch', 'host'),
                'port': int(config.get('elasticsearch','port')),
                'use_ssl': config.get('elasticsearch', 'secure'),
                'verify_certs': False,
            }],
                max_retries=5,
                retry_on_timeout=True
            )
        
        # IMPORTANT BIT: Figure out if this is ES < 6.x, 6.x or >= 7.x.
        # If so, we're using the new ES DB mappings, and need to adjust ALL
        # ES calls to match this.
        self.ESversion = int(self.ES.info()['version']['number'].split('.')[0])
        if self.ESversion >= 7:
            self.ES = SteveESWrapperSeven(self.ES)
        elif self.ESVersion >= 6:
            self.ES = SteveESWrapper(self.ES)

class ElasticSearchBackend:
    es = None
    
    def __init__(self, config):
        " Init - get config and turn it into an ES instance"
        self.index = config.get("elasticsearch", "index") if config.has_option("elasticsearch", "index") else "steve"
        self.DB = SteveDatabase(config)
        
        # Check that we have a 'steve' index. If not, create it.
        if not self.DB.ES.ES.indices.exists(self.index):
            self.DB.ES.ES.indices.create(index = self.index, body = {
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
        return self.DB.ES.exists(index=self.index, doc_type=doc, id=eid)
        
        
    
    def get_basedata(self, election):
        "Get base data from an election"
        res = self.DB.ES.get(index=self.index, doc_type="elections", id=election)
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
        self.DB.ES.index(index=self.index, doc_type="elections", id=election, body = basedata )
            
    
    def issue_get(self, electionID, issueID):
        "Get JSON data from an issue"
        issuedata = None
        ihash = ""
        iid = hashlib.sha224(electionID + "/" + issueID).hexdigest()
        res = self.DB.ES.get(index=self.index, doc_type="issues", id=iid)
        if res:
            issuedata = res['_source']
            ihash = hashlib.sha224(json.dumps(issuedata)).hexdigest()
        return issuedata, ihash
    
    
    def votes_get(self, electionID, issueID):
        "Read votes and return as a dict"
        res = self.DB.ES.search(index=self.index, doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = {}
            for entry in res['hits']['hits']:
                votes[entry['_source']['key']] = entry['_source']['data']['vote']
            return votes
        return {}
    
    
    
    def votes_get_raw(self, electionID, issueID):
        "Read votes and return raw format"
        res = self.DB.ES.search(index=self.index, doc_type="votes", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = []
            for entry in res['hits']['hits']:
                votes.append(entry['_source'])
            return votes
        return {}
    
    def vote_history(self, electionID, issueID):
        "Read vote history and return raw format"
        res = self.DB.ES.search(index=self.index, doc_type="vote_history", sort = "data.timestamp", q = "election:%s AND issue:%s" % (electionID, issueID), size = 9999)
        results = len(res['hits']['hits'])
        if results > 0:
            votes = []
            for entry in res['hits']['hits']:
                votes.append(entry['_source'])
            return votes
        return []
    
    def election_create(self,electionID, basedata):
        "Create a new election"
        self.DB.ES.index(index=self.index, doc_type="elections", id=electionID, body =
            basedata
        );
    
    def election_update(self,electionID, basedata):
        "Update an election with new data"
        self.DB.ES.index(index = self.index, doc_type = "elections", id=electionID, body = basedata)
    
    
    def issue_update(self,electionID, issueID, issueData):
        "Update an issue with new data"
        self.DB.ES.index(index = self.index, doc_type = "issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = issueData)
    
    
    def issue_list(self, election):
        "List all issues in an election"
        issues = []
        try:
            res = self.DB.ES.search(index=self.index, doc_type="issues", sort = "id", q = "election:%s" % election, size = 999, _source_include = 'id')
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
            res = self.DB.ES.search(index=self.index, doc_type="elections", sort = "id", q = "*", size = 9999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    source  = entry['_source']
                    elections.append(source['id'])
        except Exception as err:
            pass # THIS IS OKAY! On initial setup, this WILL fail until an election has been created
        return elections
    
    def vote(self,electionID, issueID, uid, vote, vhash = None):
        "Casts a vote on an issue"
        eid = hashlib.sha224(electionID + ":" + issueID + ":" + uid).hexdigest()
        now = time.time()
        if vhash:
            eid = vhash
        self.DB.ES.index(index=self.index, doc_type="votes", id=eid, body =
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
        self.DB.ES.index(index=self.index, doc_type="vote_history", body =
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
        self.DB.ES.delete(index=self.index, doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest());
        
    def issue_create(self,electionID, issueID, data):
        "Create an issue"
        self.DB.ES.index(index=self.index, doc_type="issues", id=hashlib.sha224(electionID + "/" + issueID).hexdigest(), body = data);
    
    
    
    def voter_get_uid(self, electionID, votekey):
        "Get the UID/email for a voter given the vote key hash"
        
        # First, try the raw hash as an ID
        try:
            res = self.DB.ES.get(index=self.index, doc_type="voters", id=votekey)
            if res:
                return res['_source']['uid']
        except:
            pass
        
        # Now, look for it as hash inside the doc
        try:
            res = self.DB.ES.search(index=self.index, doc_type="voters", q = "election:%s" % electionID, size = 9999)
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
        self.DB.ES.index(index=self.index, doc_type="voters", id=eid, body = {
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
        bid = self.voter_get_uid(election, xhash)
        if not bid:
            return None
        issues = self.issue_list(election)
        for issue in issues:
            vhash = hashlib.sha224(xhash + issue).hexdigest()
            try:
                self.DB.ES.delete(index=self.index, doc_type="votes", id=vhash);
            except:
                pass
        return True
    
    def voter_remove(self,election, UID):
        "Remove the voter with the given UID"
        votehash = hashlib.sha224(election + ":" + UID).hexdigest()
        self.DB.ES.delete(index=self.index, doc_type="voters", id=votehash);
    
    def voter_has_voted(self,election, issue, uid):
        "Return true if the voter has voted on this issue, otherwise false"
        eid = hashlib.sha224(election + ":" + issue + ":" + uid).hexdigest()
        try:
            return self.DB.ES.exists(index=self.index, doc_type="votes", id=eid)
        except:
            return False

    def voter_ballots(self, UID):
        """Find all elections (and ballots) this user has participated in"""
        
        # First, get all elections
        elections = {}
        
        res = self.DB.ES.search(index=self.index, doc_type="elections", sort = "id", q = "*", size = 9999)
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
        res = self.DB.ES.search(index=self.index, doc_type="voters", body = {
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