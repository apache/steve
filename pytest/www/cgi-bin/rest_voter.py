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
form = cgi.FieldStorage();

from lib import response, voter


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
    election = l[1] if len(l) > 1 else None
    issue = l[2]  if len(l) > 2 else None
    voterid = form.getvalue('uid')
    
    if not voterid and karma < 3 and (action != "request" and action != "peek"):
        response.respond(403, {'message': "Voter UID missing"})
    
    elif action == "view":
        # View a list of issues for an election
        if election and not issue:
            js = []
            elpath = os.path.join(homedir, "issues", election)
            if os.path.isdir(elpath):
                basedata = {}
                try:
                    with open(elpath + "/basedata.json", "r") as f:
                        basedata = json.loads(f.read())
                        f.close()
                    if karma < 3 and not voter.get(election, basedata, voterid):
                        raise Exception("Invalid voter ID presented")
                    issues = [ f for f in listdir(elpath) if os.path.isfile(os.path.join(elpath,f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
                    for issue in issues:
                        try:
                            with open(elpath + "/" + issue, "r") as f:
                                entry = json.loads(f.read())
                                f.close()
                                entry['id'] = issue.strip(".json")
                                entry['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (os.environ['SERVER_NAME'], election, issue.strip(".json"))
                                entry['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (os.environ['SERVER_NAME'], election, issue.strip(".json"))
                                entry['hasVoted'] = voter.hasVoted(election, issue, voterid)
                                js.append(entry)
                        except Exception as err:
                            response.respond(500, {'message': 'Could not load issues: %s' % err})
                except Exception as err:
                    response.respond(500, {'message': 'Could not load base data: %s' % err})
                if 'hash' in basedata:
                    del basedata['hash']
                response.respond(200, {'base_data': basedata, 'issues': js, 'baseurl': "https://%s/steve/election?%s" % (os.environ['SERVER_NAME'], election)})
            else:
                response.respond(404, {'message': 'No such election'})
                
        # View a speficic issue
        elif election and issue:
            js = []
            elpath = os.path.join(homedir, "issues", election)
            issuepath = os.path.join(homedir, "issues", election, issue)
            if os.path.isfile(issuepath + ".json"):
                basedata = {}
                try:
                    with open(elpath + "/basedata.json", "r") as f:
                        basedata = json.loads(f.read())
                        f.close()
                    if karma < 3 and not voter.get(election, basedata, voterid):
                        raise Exception("Invalid voter ID presented")
                    with open(issuepath + ".json", "r") as f:
                        entry = json.loads(f.read())
                        f.close()
                        entry['id'] = issue.strip(".json")
                        entry['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (os.environ['SERVER_NAME'], election, issue)
                        entry['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (os.environ['SERVER_NAME'], election, issue)
                        response.respond(200, {'issue': entry})
                except Exception as err:
                    response.respond(500, {'message': "Could not load issue: %s" % err})
            else:
                response.respond(404, {'message': 'No such issue'})
        else:
            response.respond(404, {'message': 'No election ID supplied'})
    elif action == "vote" and election and issue and voterid:
        try:
            elpath = os.path.join(homedir, "issues", election)
            issuepath = os.path.join(homedir, "issues", election, issue) + ".json"
            if os.path.isdir(elpath) and os.path.isfile(issuepath):
                basedata = {}
                issuedata = {}
                with open(elpath + "/basedata.json", "r") as f:
                    basedata = json.loads(f.read())
                    f.close()
                with open(issuepath, "r") as f:
                    issuedata = json.loads(f.read())
                    f.close()
                email = voter.get(election, basedata, voterid)
                if not email:
                    response.respond(403, {'message': 'Could not save vote: Invalid voter ID presented'})
                else:
                    vote = form.getvalue('vote')
                    if not vote:
                        response.respond(500, {'message': 'Please specify a vote'})
                    else:
                        double = False
                        invalid = False
                        letters = ['y','n','a']
                        if issuedata['type'].find("stv") == 0:
                            letters = [chr(i) for i in range(ord('a'),ord('a') + len(issuedata['candidates']))]
                        for char in letters:
                            if vote.count(char) > 1:
                                double = True
                                break
                        for char in vote:
                            if not char in letters:
                                invalid = True
                                break
                        if double:
                            response.respond(500, {'message': "Vote contains duplicate characters"})
                        elif invalid:
                            response.respond(500, {'message': "Vote contains invalid characters. Accepted are: %s" % ", ".join(letters)})
                        else:
                            votes = {}
                            if os.path.isfile(issuepath + ".votes"):
                                with open(issuepath + ".votes", "r") as f:
                                    votes = json.loads(f.read())
                                    f.close()
                            votes[voterid] = vote
                            with open(issuepath + ".votes", "w") as f:
                                f.write(json.dumps(votes))
                                f.close()
                            votehash = hashlib.sha224(basedata['hash'] + voterid + vote + email).hexdigest()
                            voter.email(email, "Vote registered: %s (%s)" % (issue, issuedata['title']), "This is a receipt that your vote was registered for issue #%s:\n\nElection: %s (%s)\nIssue: %s (%s)\nVote cryptohash: %s" % (issue, basedata['title'], election, issuedata['title'], issue, votehash))
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
                elpath = os.path.join(homedir, "issues", election)
                if os.path.isdir(elpath):
                    basedata = {}
                    with open(elpath + "/basedata.json", "r") as f:
                        basedata = json.loads(f.read())
                        f.close()
                    if 'open' in basedata and basedata['open'] == "true":
                        uid, xhash = voter.add(election, basedata, email)
                        voter.email(email, "Your voter link for %s" % basedata['title'], "Your personal vote link is: %s/election.html?%s/%s\nDo not share this link with anyone." % (config.get("general", "rooturl"), election, uid))
                        response.respond(200, {'message': "Voter ID sent via email"})
                    else:
                        response.respond(403, {'message': "Could not request voter ID: This eleciton is closed for the public"})
                else:
                    response.respond(404, {'message': 'Could not request voter ID: No such election'})
                        
            except Exception as err:
                response.respond(500, {'message': 'Could not create voter ID: %s' % err})
    elif action == "peek" and election:
        try:
            elpath = os.path.join(homedir, "issues", election)
            if os.path.isdir(elpath):
                basedata = {}
                with open(elpath + "/basedata.json", "r") as f:
                    basedata = json.loads(f.read())
                    f.close()
                if 'open' in basedata and basedata['open'] == "true":
                    if 'hash' in basedata:
                        del basedata['hash']
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