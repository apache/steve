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
import os, sys, json, re, time, base64, cgi, subprocess, hashlib
version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
from os import listdir
from os.path import isdir, isfile
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


whoami = os.environ['REMOTE_USER'] if 'REMOTE_USER' in os.environ else None

from lib import response, voter, election, form, constants

if not whoami:
    response.respond(403, {'message': 'Could not verify your identity: No auth scheme found'})
elif not config.has_option('karma', whoami):
    response.respond(403, {'message': 'Could not verify your identity: No such user: %s' % whoami})
else:
    
    karma = int(config.get("karma", whoami))
    
    # Figure out what to do and where
    if pathinfo:
        l = pathinfo.split("/")
        if l[0] == "":
            l.pop(0)
        action = l[0]
        electionID = l[1] if len(l) > 1 else None
        if electionID:
            if re.search(r"([^A-Za-z0-9-.])", electionID):
                response.respond(400, {'message': "Invalid election ID supplied, must be [A-Za-z0-9-.]+"})
                sys.exit(0) # BAIL!
 
        # List all existing/previous elections?
        if action == "list":
            output = []
            errors = []
            path = os.path.join(homedir, "issues")
            elections = election.listElections()
            for electionID in elections:
                try:
                    basedata = election.getBasedata(electionID, hideHash = True)
                    if karma >= 5 or ('owner' in basedata and basedata['owner'] == whoami):
                        output.append(basedata)
                except Exception as err:
                    errors.append("Could not parse election '%s': %s" % (electionID, err))
            if len(errors) > 0:
                response.respond(206, { 'elections': output, 'errors': errors})
            else:
                response.respond(200, { 'elections': output})
        # Set up new election?
        elif action == "setup":
            if karma >= 5: # karma of 5 required to set up an election base
                if electionID:
                    if election.exists(electionID):
                        response.respond(403, {'message': "Election already exists!"})
                    else:
                        try:
                            required = ['title','owner','monitors']
                            xr = required
                            for i in required:
                                if not form.getvalue(i):
                                    raise Exception("Required fields missing: %s" % ", ".join(xr))
                                else:
                                    xr.pop(0)
                            election.createElection(
                                electionID,
                                form.getvalue('title'),
                                form.getvalue('owner'),
                                [x.strip() for x in form.getvalue('monitors').split(",")],
                                form.getvalue('starts'),
                                form.getvalue('ends'),
                                form.getvalue('open')
                            )
                            response.respond(201, {'message': 'Created!', 'id': electionID})
                        except Exception as err:
                            response.respond(500, {'message': "Could not create electionID: %s" % err})
                else:
                    response.respond(400, {'message': "No election name specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
                
        # Create an issue in an election
        elif action == "create":
            if karma >= 4: # karma of 4 required to set up an issue for the election
                if electionID:
                    issue = l[2] if len(l) > 2 else None
                    if not issue:
                        response.respond(400, {'message': 'No issue ID specified'})
                    elif re.search(r"([^A-Za-z0-9-.])", issue):
                        response.respond(400, {'message': "Invalid issue ID supplied, must be [A-Za-z0-9-.]+"})
                    else:
                        issuepath = os.path.join(homedir, "issues", electionID, issue)
                        if os.path.isfile(issuepath + ".json"):
                            response.respond(400, {'message': 'An issue with this ID already exists'})
                        else:
                            try:
                                required = ['title','type']
                                xr = required
                                for i in required:
                                    if not form.getvalue(i):
                                        raise Exception("Required fields missing: %s" % ", ".join(xr))
                                    else:
                                        xr.pop(0)
                                if not form.getvalue('type') in constants.VALID_VOTE_TYPES:
                                    raise Exception('Invalid vote type: %s' % form.getvalue('type'))
                                with open(issuepath + ".json", "w") as f:
                                    candidates = []
                                    c = []
                                    s = []
                                    if form.getvalue('candidates'):
                                        try:
                                            c = json.loads(form.getvalue('candidates'))
                                            if form.getvalue('statements'):
                                                try:
                                                    s = json.loads(form.getvalue('statements'))
                                                except:
                                                    s = form.getvalue('statements').split("\n")
                                        except:
                                            c = form.getvalue('candidates').split("\n")
                                        z = 0
                                        for entry in c:
                                            candidates.append({'name': entry.strip(), 'statement': s[z] if len(s) > z else ""})
                                            z += 1
                                    f.write(json.dumps({
                                        'title': form.getvalue('title'),
                                        'description': form.getvalue('description'),
                                        'type': form.getvalue('type'),
                                        'candidates': candidates,
                                        'seconds': [x.strip() for x in form.getvalue('seconds').split("\n")] if form.getvalue('seconds') else [],
                                        'nominatedby': form.getvalue('nominatedby')
                                    }))
                                    f.close()
                                response.respond(201, {'message': 'Created!', 'id': issue})
                            except Exception as err:
                                response.respond(500, {'message': "Could not create issue: %s" % err})
                else:
                    response.respond(400, {'message': "No election specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        
        # Delete an issue in an election
        elif action == "delete":
            if karma >= 4: # karma of 4 required to set up an issue for the election
                if electionID:
                    issue = l[2] if len(l) > 2 else None
                    if not issue:
                        response.respond(400, {'message': 'No issue ID specified'})
                    else:
                        if election.exists(electionID, issue):
                            try:
                                election.deleteIssue(electionID, issue)
                                response.respond(200, {'message': "Issue deleted"})
                            except Exception as err:
                                response.respond(500, {'message': 'Could not delete issue: %s' % err})
                        else:
                            response.respond(404, {'message': "No such issue!"})
                else:
                    response.respond(400, {'message': "No electionID specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        
        
        
        # Edit an issue or election
        elif action == "edit":
            issue = l[2] if len(l) > 2 else None
            if (issue and karma >= 4) or (karma >= 5 and electionID):
                if electionID:
                    if not issue:
                        elpath = os.path.join(homedir, "issues", electionID)
                        if not os.path.isdir(elpath) or not os.path.isfile(elpath+"/basedata.json"):
                            response.respond(404, {'message': 'No such issue'})
                        else:
                            try:
                                js = {}
                                with open(elpath + "/basedata.json", "r") as f:
                                    js = json.loads(f.read())
                                    f.close()
                                fields = ['title','owner','monitors','starts','ends']
                                for field in fields:
                                    val = form.getvalue(field)
                                    if val:
                                        if field == "monitors":
                                            val = [x.strip() for x in val.split(",")]
                                        js[field] = val
                                with open(elpath + "/basedata.json", "w") as f:
                                    f.write(json.dumps(js))
                                    f.close()
                                response.respond(200, {'message': "Changed saved"})
                            except Exception as err:
                                response.respond(500, {'message': "Could not edit election: %s" % err})
                    else:
                        issuepath = os.path.join(homedir, "issues", electionID, issue)
                        if not os.path.isfile(issuepath + ".json"):
                            response.respond(404, {'message': 'No such issue'})
                        else:
                            try:
                                js = {}
                                with open(issuepath + ".json", "r") as f:
                                    js = json.loads(f.read())
                                    f.close()
                                fields = ['title','description','type','statements','candidates','seconds','nominatedby']
                                statements = []
                                for field in fields:
                                    val = form.getvalue(field)
                                    if val:
                                        if field == "candidates":
                                            try:
                                                xval = json.loads(val)
                                            except:
                                                xval = val.split("\n")
                                            val = []
                                            z = 0
                                            for entry in xval:
                                                val.append({'name': entry.strip(), 'statement': statements[z] if len(statements) > z else ""})
                                                z += 1
                                        if field == "statements":
                                            try:
                                                xval = json.loads(val)
                                            except:
                                                xval = val.split("\n")
                                            val = []
                                            for entry in xval:
                                                statements.append(entry)
                                        if field == "seconds":
                                            val = [x.strip() for x in val.split("\n")]
                                        js[field] = val
                                with open(issuepath + ".json", "w") as f:
                                    f.write(json.dumps(js))
                                    f.close()
                                response.respond(200, {'message': "Changed saved"})
                            except Exception as err:
                                response.respond(500, {'message': "Could not edit issue: %s" % err})
                else:
                    response.respond(400, {'message': "No election specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        
        # Edit/add a statement
        elif action == "statement":
            issue = l[2] if len(l) > 2 else None
            if (issue and karma >= 4):
                issuepath = os.path.join(homedir, "issues", electionID, issue)
                if not os.path.isfile(issuepath + ".json"):
                    response.respond(404, {'message': 'No such issue'})
                else:
                    try:
                        js = {}
                        with open(issuepath + ".json", "r") as f:
                            js = json.loads(f.read())
                            f.close()
                        
                        cand = form.getvalue('candidate')
                        stat = form.getvalue('statement')
                        found = False
                        for entry in js['candidates']:
                            if entry['name'] == cand:
                                found = True
                                entry['statement'] = stat
                                break
                        if not found:
                            raise Exception("No such candidate: " + cand)                    
                        with open(issuepath + ".json", "w") as f:
                            f.write(json.dumps(js))
                            f.close()
                        response.respond(200, {'message': "Changed saved"})
                    except Exception as err:
                        response.respond(500, {'message': "Could not edit issue: %s" % err})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
                
        # Edit/add a statement
        elif action == "addcandidate":
            issue = l[2] if len(l) > 2 else None
            if (issue and karma >= 4):
                issuepath = os.path.join(homedir, "issues", electionID, issue)
                if not os.path.isfile(issuepath + ".json"):
                    response.respond(404, {'message': 'No such issue'})
                else:
                    try:
                        js = {}
                        with open(issuepath + ".json", "r") as f:
                            js = json.loads(f.read())
                            f.close()
                        
                        cand = form.getvalue('candidate')
                        stat = form.getvalue('statement')
                        found = False
                        for entry in js['candidates']:
                            if entry['name'] == cand:
                                found = True
                                break
                        if found:
                            raise Exception("Candidate already exists: " + cand)
                        else:
                            js['candidates'].append( {
                                'name': cand,
                                'statement': stat
                            })
                        with open(issuepath + ".json", "w") as f:
                            f.write(json.dumps(js))
                            f.close()
                        response.respond(200, {'message': "Changed saved"})
                    except Exception as err:
                        response.respond(500, {'message': "Could not edit issue: %s" % err})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        elif action == "delcandidate":
            issue = l[2] if len(l) > 2 else None
            if (issue and karma >= 4):
                issuepath = os.path.join(homedir, "issues", electionID, issue)
                if not os.path.isfile(issuepath + ".json"):
                    response.respond(404, {'message': 'No such issue'})
                else:
                    try:
                        js = {}
                        with open(issuepath + ".json", "r") as f:
                            js = json.loads(f.read())
                            f.close()
                        
                        cand = form.getvalue('candidate')
                        found = False
                        i = 0
                        for entry in js['candidates']:
                            if entry['name'] == cand:
                                js['candidates'].pop(i)
                                found = True
                                break
                            i += 1
                        if not found:
                            raise Exception("Candidate does nost exist: " + cand)
                        with open(issuepath + ".json", "w") as f:
                            f.write(json.dumps(js))
                            f.close()
                        response.respond(200, {'message': "Changed saved"})
                    except Exception as err:
                        response.respond(500, {'message': "Could not edit issue: %s" % err})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        elif action == "view" and karma >= 3:
            # View a list of issues for an election
            if electionID:
                js = []
                if election.exists(electionID):
                    basedata = {}
                    try:
                        basedata = election.getBasedata(electionID, hideHash = True)
                        for issue in election.listIssues(electionID):
                            try:
                                entry = election.getIssue(electionID, issue)
                                js.append(entry)
                            except Exception as err:
                                response.respond(500, {'message': 'Could not load issues: %s' % err})
                    except Exception as err:
                        response.respond(500, {'message': 'Could not load base data: %s' % err})
                    if 'hash' in basedata:
                        del basedata['hash']
                    response.respond(200, {'base_data': basedata, 'issues': js, 'baseurl': "https://%s/steve/election.html?%s" % (config.get("general", "rooturl"), electionID)})
                else:
                    response.respond(404, {'message': 'No such election'})
            else:
                    response.respond(404, {'message': 'No such election'})
        # Delete an issue
        elif action == "delete" and electionID and issue:
            if electionID and issue:
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                    issuedata = election.getIssue(electionID, issue)
                    if issuedata:
                        election.deleteIssue(electionID, issue)
                        response.respond(200, {'message': 'Issue deleted'})
                    else:
                        response.respond(404, {'message': "Issue not found"})
                else:
                    response.respond(403, {'message': "You do not have karma to delete this issue"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})
        
        # Send issue hash to monitors
        elif action == "debug" and electionID:
            if election.exists(electionID):
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                    ehash, debug = election.getHash(electionID)
                    for email in basedata['monitors']:
                        voter.email(email, "Monitoring update for election #%s" % electionID, debug)
                    response.respond(200, {'message': "Debug sent to monitors", 'hash': ehash, 'debug': debug})
                else:
                    response.respond(403, {'message': "You do not have karma to do this"})
            else:
                    response.respond(404, {'message': 'No such election'})
        
        # Get a temp voter ID for peeking
        elif action == "temp" and electionID:
            if electionID and election.exists(electionID):
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                        voterid, xhash = voter.add(electionID, basedata, whoami + "@stv")
                        response.respond(200, {'id': voterid})
                else:
                    response.respond(403, {'message': "You do not have karma to peek at this election"})
            else:
                    response.respond(404, {'message': 'No such election'})
            
        # Invite folks to the election
        elif action == "invite" and karma >= 3:
            # invite one or more people to an election
            if electionID:
                email = form.getvalue('email')
                msgtype = form.getvalue('msgtype')
                msgtemplate = form.getvalue('msgtemplate')
                if not email or len(email) > 300 or not re.match(r"([^@]+@[^@]+)", email):
                    response.respond(400, {'message': 'Could not request voter ID: Invalid email address specified'})
                elif not msgtemplate or len(msgtemplate) < 10:
                    response.respond(400, {'message': 'No message template specified'})
                else:
                    js = []
                    if election.exists(electionID):
                        basedata = {}
                        try:
                            basedata = election.getBasedata(electionID)
                            if (not 'open' in basedata or basedata['open'] != "true") and msgtype == "open":
                                raise Exception("An open vote invite was requested, but this election is not public")
                            if msgtype != "open":
                                voterid, xhash = voter.add(electionID, basedata, email)
                                message = msgtemplate.replace("$votelink", "%s/election.html?%s/%s" % (config.get("general", "rooturl"), electionID, voterid))
                                message = message.replace("$title", basedata['title'])
                                subject = "Election open for votes: %s (%s)" % (electionID, basedata['title'])
                                voter.email(email, subject, message)
                            else:
                                message = msgtemplate.replace("$votelink", "%s/request_link.html?%s" % (config.get("general", "rooturl"), electionID))
                                message = message.replace("$title", basedata['title'])
                                subject = "Public electionIopen for votes: %s (%s)" % (electionID, basedata['title'])
                                voter.email(email, subject, message)
                            response.respond(200, {'message': "Vote link sent"})
                        except Exception as err:
                            response.respond(500, {'message': 'Could not load base data: %s' % err})
                        
                        response.respond(200, {'message': "Vote link sent to %s" % email})
                    else:
                        response.respond(404, {'message': 'No such election'})
            else:
                    response.respond(404, {'message': 'No such election'})
        # Tally an issue
        elif action == "tally" and electionID:
            issue = l[2] if len(l) > 2 else None
            if electionID and issue:
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                    issuedata = election.getIssue(electionID, issue)
                    votes = election.getVotes(electionID, issue)
                    if issuedata and votes:
                        if issuedata['type'].startswith("stv"):
                            numseats = int(issuedata['type'][3])
                            winners, winnernames, debug = election.stv(issuedata['candidates'], votes, numseats, shuffle = True)
                            response.respond(200, {'votes': len(votes), 'winners': winners, 'winnernames': winnernames, 'debug': debug})
                        elif issuedata['type'] == "yna":
                            yes, no, abstain = election.yna(votes)
                            response.respond(200, {'votes': len(votes), 'yes': yes, 'no': no, 'abstain': abstain})
                        else:
                            response.respond(500, {'message': "Unknown vote type"})
                    elif not votes:
                        response.respond(404, {'message': "No votes found"})
                    else:
                        response.respond(404, {'message': "Issue not found"})
                else:
                    response.respond(403, {'message': "You do not have karma to tally the votes here"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})
        # Close an election
        elif action == "close" and electionID:
            reopen = form.getvalue('reopen')
            if election.exists(electionID):
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                    try:
                        election.close(electionID, reopen=reopen)
                        if reopen:
                            response.respond(200, {'message': "Election reopened"})
                        else:
                            ehash, debug = election.getHash(electionID)
                            for email in basedata['monitors']:
                                voter.email(email, "Monitoring update for election #%s: Election closed!" % electionID, debug)
                            response.respond(200, {'message': "Election closed"})
                    except Exception as err:
                        response.respond(500, {'message': "Could not close election: %s" % err})
                else:
                    response.respond(403, {'message': "You do not have karma to tally the votes here"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})      
        else:
            response.respond(400, {'message': "No (or invalid) action supplied"})
    else:
        response.respond(500, {'message': "No path_info supplied"})
