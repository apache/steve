#!/usr/bin/env python
#####
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#####
import os, sys, json, re, time, base64, cgi, subprocess, hashlib, re
from os import listdir
version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
    

path = os.path.abspath(os.getcwd())

sys.path.append(path)
sys.path.append(os.path.basename(sys.argv[0]))
if 'SCRIPT_FILENAME' in os.environ:
    sys.path.insert(0, os.path.basename(os.environ['SCRIPT_FILENAME']))

# Fetch config (hack, hack, hack)
config = configparser.RawConfigParser()
config.read(path + '/../../steve.cfg')

# Some quick paths
homedir = config.get("general", "homedir")
pathinfo = os.environ['PATH_INFO'] if 'PATH_INFO' in os.environ else None

from lib import response, voter, election, form


whoami = os.environ['REMOTE_USER'] if 'REMOTE_USER' in os.environ else None
karma = 0
if whoami and config.has_option("karma", whoami):
    karma = int(config.get("karma", whoami))

# Figure out what to do and where
if pathinfo:
    l = pathinfo.split("/")
    if l[0] == "":
        l.pop(0)
    action = l[0]
    electionID = l[1] if len(l) > 1 else None
    issueID = l[2]  if len(l) > 2 else None
    voterID = form.getvalue('uid')
    
    if not voterID and karma < 3 and (action != "request" and action != "peek"):
        response.respond(403, {'message': "Voter UID missing"})
    elif electionID and re.search(r"([^A-Za-z0-9-.])", electionID):
        response.respond(400, {'message': "Invalid election ID specified"})
    elif issueID and re.search(r"([^A-Za-z0-9-.])", issueID):
        response.respond(400, {'message': "Invalid issue ID specified"})
    elif action == "view":
        # View a list of issues for an election
        if electionID and not issueID:
            js = []
            if election.exists(electionID):
                try:
                    basedata = election.getBasedata(electionID)
                    if not basedata:
                        raise Exception("Could not load base data")
                    if karma < 3 and not voter.get(electionID, basedata, voterID):
                        raise Exception("Invalid voter ID presented")
                    if 'closed' in basedata and basedata['closed'] == True:
                        raise Exception("This election has closed")
                    for issueID in election.listIssues(electionID):
                        try:
                            entry = election.getIssue(electionID, issueID)
                            entry['hasVoted'] = voter.hasVoted(electionID, issueID, voterID)
                            js.append(entry)
                        except Exception as err:
                            response.respond(500, {'message': 'Could not load issues: %s' % err})
                except Exception as err:
                    response.respond(500, {'message': 'Could not load base data: %s' % err})
                if 'hash' in basedata:
                    del basedata['hash']
                response.respond(200, {'base_data': basedata, 'issues': js, 'baseurl': config.get("general", "rooturl")})
            else:
                response.respond(404, {'message': 'No such election'})
                
        # View a speficic issue
        elif electionID and issueID:
            js = []
            issuedata = election.getIssue(electionID, issueID)
            if issuedata:
                try:
                    basedata = election.getBasedata(electionID)
                    if karma < 3 and not voter.get(electionID, basedata, voterID):
                        raise Exception("Invalid voter ID presented")
                    if 'closed' in basedata and basedata['closed'] == True:
                        raise Exception("This election has closed")
                    entry = election.getIssue(electionID, issueID)
                    response.respond(200, {'issue': entry})
                except Exception as err:
                    response.respond(500, {'message': "Could not load issue: %s" % err})
            else:
                response.respond(404, {'message': 'No such issue'})
        else:
            response.respond(404, {'message': 'No election ID supplied'})
            
    elif action == "ballots":
        # We defer to the gateway to provide us with UID here
        response.respond(200, voter.ballots())
        
    elif action == "regenerate" and electionID and issueID:
        # Regenerate a ballot, scrub all votes.
        xhash = issueID
        basedata = election.getBasedata(electionID)
        if basedata:
            response.respond(200, voter.regenerate(electionID, basedata, xhash))
        else:
            response.respond(404, {'message': "No such election"})
            
    elif action == "vote" and electionID and issueID and voterID:
        try:
            basedata = election.getBasedata(electionID)
            issuedata = election.getIssue(electionID, issueID)
            if basedata and issuedata:
                if 'closed' in basedata and basedata['closed'] == True:
                        raise Exception("This election has closed")
                email = voter.get(electionID, basedata, voterID)
                if not email:
                    response.respond(403, {'message': 'Could not save vote: Invalid voter ID presented'})
                else:
                    vote = form.getvalue('vote')
                    if not vote:
                        response.respond(500, {'message': 'Please specify a vote'})
                    else:
                        invalid = election.invalidate(issuedata, vote)
                        if invalid:
                            response.respond(500, {'message': invalid})
                        else:
                            votehash = election.vote(electionID, issueID, voterID, vote)
                            voteuid = hashlib.sha224(voterID).hexdigest()
                            # Catch proxy-emails
                            m = re.match(r"^(.+@.*?[a-zA-Z])-[^.]+$", email)
                            if m:
                                email = m.group(1)
                            voter.email(email, "Vote registered: %s (%s)" % (issueID, issuedata['title']), "This is a receipt that your vote was registered for issue #%s:\n\nElection: %s (%s)\nIssue: %s (%s)\nVote cryptohash: %s\nVote UID: %s" % (issueID, basedata['title'], electionID, issuedata['title'], issueID, votehash, voteuid))
                            response.respond(200, {'message': 'Vote saved!'})
            else:
                response.respond(404, {'message': 'Could not save vote: No such election or issue'})
                    
        except Exception as err:
            response.respond(500, {'message': 'Could not save vote: %s' % err})
            
            
    elif action == "request" and election:
        email = form.getvalue('email')
        if not email or len(email) > 300 or not re.match(r"([^@]+@[^@]+)", email):
            response.respond(400, {'message': 'Could not request voter ID: Invalid email address specified'})
        else:
            try:
                basedata = election.getBasedata(electionID)
                if basedata:
                    if 'closed' in basedata and basedata['closed'] == True:
                        raise Exception("This election has closed")
                    if 'open' in basedata and basedata['open'] == "true":
                        uid, xhash = voter.add(electionID, basedata, email)
                        voter.email(email, "Your voter link for %s" % basedata['title'], "Your personal vote link is: %s/election.html?%s/%s\nDo not share this link with anyone." % (config.get("general", "rooturl"), electionID, uid))
                        response.respond(200, {'message': "Voter ID sent via email"})
                    else:
                        response.respond(403, {'message': "Could not request voter ID: This eleciton is closed for the public"})
                else:
                    response.respond(404, {'message': 'Could not request voter ID: No such election'})
                        
            except Exception as err:
                response.respond(500, {'message': 'Could not create voter ID: %s' % err})
    elif action == "peek" and election:
        try:
            basedata = election.getBasedata(electionID, hideHash=True)
            if basedata:
                if 'closed' in basedata and basedata['closed'] == True:
                        raise Exception("This election has closed")
                if 'open' in basedata and basedata['open'] == "true":
                    response.respond(200, { 'base_data': basedata } )
                else:
                    response.respond(403, {'message': 'This election is not open to the public'})
            else:
                response.respond(404, {'message': 'Could not request data: No such election'})
                    
        except Exception as err:
            response.respond(500, {'message': 'Could not load election data: %s' % err})
    else:
        response.respond(400, {'message': 'Invalid action supplied'})
else:
    response.respond(500, {'message': 'No path info supplied, aborting'})