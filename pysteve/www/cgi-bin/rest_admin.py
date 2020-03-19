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
            if karma >= 4: # karma of 4 required to set up an election base
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
                                if not election.validType(form.getvalue('type')):
                                    raise Exception('Invalid vote type: %s' % form.getvalue('type'))
                                else:
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
                                        for entry in [x for x in c if x and x.strip()]: # Skip blank entries
                                            candidates.append({'name': entry.strip(), 'statement': s[z] if len(s) > z else ""})
                                            z += 1
                                    # HACK: If candidate parsing is outsourced, let's do that instead (primarily for COP)
                                    voteType = election.getVoteType({'type': form.getvalue('type')})
                                    if 'parsers' in voteType and 'candidates' in voteType['parsers']:
                                        candidates = voteType['parsers']['candidates'](form.getvalue('candidates'))
                                        
                                    election.createIssue(electionID, issue, {
                                        'election': electionID,
                                        'id': issue,
                                        'title': form.getvalue('title'),
                                        'description': form.getvalue('description'),
                                        'type': form.getvalue('type'),
                                        'candidates': candidates,
                                        'seconds': [x.strip() for x in form.getvalue('seconds').split("\n")] if form.getvalue('seconds') else [],
                                        'nominatedby': form.getvalue('nominatedby')
                                    })
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
                        if not election.exists(electionID,):
                            response.respond(404, {'message': 'No such election'})
                        else:
                            try:
                                basedata = election.getBasedata(electionID)
                                fields = ['title','owner','monitors','starts','ends']
                                for field in fields:
                                    val = form.getvalue(field)
                                    if val:
                                        if field == "monitors":
                                            val = [x.strip() for x in val.split(",")]
                                        basedata[field] = val
                                election.updateElection(electionID, basedata)
                                response.respond(200, {'message': "Changed saved"})
                            except Exception as err:
                                response.respond(500, {'message': "Could not edit election: %s" % err})
                    else:
                        if not election.exists(electionID, issue):
                            response.respond(404, {'message': 'No such issue'})
                        else:
                            try:
                                issuedata = election.getIssue(electionID, issue)
                                fields = ['title','description','type','statements','seconds_txt','candidates','seconds','nominatedby']
                                statements = []
                                seconds = []
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
                                                val.append({
                                                    'name': entry.strip(),
                                                    'statement': statements[z] if len(statements) > z else "",
                                                    'seconds_txt': seconds[z] if len(seconds) > z else ""
                                                    })
                                                z += 1
                                        if field == "statements":
                                            try:
                                                xval = json.loads(val)
                                            except:
                                                xval = val.split("\n")
                                            val = []
                                            for entry in xval:
                                                statements.append(entry)
                                        if field == "seconds_txt":
                                            try:
                                                xval = json.loads(val)
                                            except:
                                                xval = val.split("\n")
                                            val = []
                                            for entry in xval:
                                                seconds.append(entry)
                                        if field == "seconds":
                                            val = [x.strip() for x in val.split("\n")]
                                        
                                            
                                        # HACK: If field  parsing is outsourced, let's do that instead (primarily for COP)
                                        voteType = election.getVoteType(issuedata)
                                        if 'parsers' in voteType and field in voteType['parsers']:
                                            val = voteType['parsers'][field](form.getvalue(field))
                                            
                                        issuedata[field] = val
                                election.updateIssue(electionID, issue, issuedata)
                                response.respond(200, {'message': "Changed saved"})
                            except Exception as err:
                                response.respond(500, {'message': "Could not edit issue: %s" % err})
                else:
                    response.respond(400, {'message': "No election specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        
        elif action == "view" and karma >= 2:
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
                    response.respond(200, {'base_data': basedata, 'issues': js, 'baseurl': "%s/election.html?%s" % (config.get("general", "rooturl"), electionID)})
                else:
                    response.respond(404, {'message': 'No such election: %s' % electionID})
            else:
                    response.respond(404, {'message': 'Invalid election ID'})
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
                        voter.email(email, "Monitoring update for election #%s: %s" % (electionID, basedata['title']), debug)
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
                proxy = None
                m = re.match(r"^(\S+)\s+(\S+)$", email)
                if m:
                    email = m.group(1)
                    proxy = m.group(2)
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
                                # If we have a proxy, we have to append the proxy name
                                # so as to not override the voters own ID
                                mailID = email
                                if proxy:
                                    mailID = "%s-%s" % (email, proxy)
                                # Generate voter ID
                                voterid, xhash = voter.add(electionID, basedata, mailID)
                                message = msgtemplate.replace("$votelink", "%s/election.html?%s/%s" % (config.get("general", "rooturl"), electionID, voterid))
                                message = message.replace("$title", basedata['title'])
                                subject = "Election open for votes: %s (%s)" % (electionID, basedata['title'])
                                if proxy:
                                    subject = "%s [PROXY FOR: %s]" % (subject, proxy)
                                voter.email(email, subject, message)
                            else:
                                message = msgtemplate.replace("$votelink", "%s/request_link.html?%s" % (config.get("general", "rooturl"), electionID))
                                message = message.replace("$title", basedata['title'])
                                subject = "Public election open for votes: %s (%s)" % (electionID, basedata['title'])
                                voter.email(email, subject, message)
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
                # Allow access at all times to owners/admins, monitors after closed
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami) or \
                (karma >= 2 and 'open' in basedata and basedata['open'] == False):
                    issuedata = election.getIssue(electionID, issue)
                    votes = election.getVotes(electionID, issue)
                    if issuedata and votes:
                        if election.validType(issuedata['type']):
                            result , pp = election.tally(votes, issuedata)
                            response.respond(200, result)
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
            ro = form.getvalue('reopen')
            if ro and ro == "true":
                ro = True
            else:
                ro = False
            if election.exists(electionID):
                basedata = election.getBasedata(electionID)
                if karma >= 4 or ('owner' in basedata and basedata['owner'] == whoami):
                    try:
                        election.close(electionID, reopen=ro)
                        ehash, debug = election.getHash(electionID)
                        if ro:
                            for email in basedata['monitors']:
                                voter.email(email, "Monitoring update for election #%s: Election reopened!" % electionID, debug)
                            response.respond(200, {'message': "Election reopened"})
                        else:
                            murl =  "%s/admin/tally.html?%s" % (config.get("general", "rooturl"), electionID)
                            for email in basedata['monitors']:
                                voter.email(email, "Monitoring update for election #%s: Election closed!" % electionID, "%s\n\nFinal tally available at: %s" % (debug, murl))
                            response.respond(200, {'message': "Election closed"})
                    except Exception as err:
                        response.respond(500, {'message': "Could not close election: %s" % err})
                else:
                    response.respond(403, {'message': "You do not have karma to tally the votes here"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})
        # Get registered vote stpye
        elif action == "types":
            types = {}
            for vtype in constants.VOTE_TYPES:
                types[vtype['key']] = vtype['description']
            response.respond(200, {'types': types})
        
        # Get vote data
        elif action == "monitor" and electionID:
            issue = l[2] if len(l) > 2 else None
            if electionID and issue:
                basedata = election.getBasedata(electionID, hideHash=True)
                if karma >= 2 or ('owner' in basedata and basedata['owner'] == whoami):
                    issuedata = election.getIssue(electionID, issue)
                    votes = election.getVotesRaw(electionID, issue)
                    jvotes = {}
                    for vote in votes:
                        jvotes[hashlib.sha224(vote['key']).hexdigest()] = {
                            'vote': vote['data']['vote'],
                            'timestamp': vote['data']['timestamp']
                        } # yeah, let's not show the actual UID here..
                    if issuedata and votes:
                        if election.validType(issuedata['type']):
                            ehash, blergh = election.getHash(electionID)
                            response.respond(200, {
                                'issue': issuedata,
                                'base': basedata,
                                'votes': jvotes,
                                'hash': ehash
                            })
                        else:
                            response.respond(500, {'message': "Unknown vote type"})
                    elif issuedata and not votes:
                        response.respond(404, {'message': "No votes found"})
                    else:
                        response.respond(404, {'message': "Issue not found"})
                else:
                    response.respond(403, {'message': "You do not have karma to tally the votes here"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})
        # Vote backlog, including all recasts
        elif action == "backlog" and electionID:
            issue = l[2] if len(l) > 2 else None
            if electionID and issue:
                basedata = election.getBasedata(electionID, hideHash=True)
                if karma >= 2 or ('owner' in basedata and basedata['owner'] == whoami):
                    issuedata = election.getIssue(electionID, issue)
                    votes = election.getVoteHistory(electionID, issue)
                    jvotes = []
                    for vote in votes:
                        jvotes.append({
                            'vote': vote['data']['vote'],
                            'timestamp': vote['data']['timestamp'],
                            'uid': hashlib.sha224(vote['key']).hexdigest()
                        })
                    if issuedata and votes:
                        if election.validType(issuedata['type']):
                            ehash, blergh = election.getHash(electionID)
                            response.respond(200, {
                                'issue': issuedata,
                                'base': basedata,
                                'history': jvotes,
                                'hash': ehash
                            })
                        else:
                            response.respond(500, {'message': "Unknown vote type"})
                    elif issuedata and not votes:
                        response.respond(404, {'message': "No votes found"})
                    else:
                        response.respond(404, {'message': "Issue not found"})
                else:
                    response.respond(403, {'message': "You do not have karma to tally the votes here"})
            else:
                    response.respond(404, {'message': 'No such election or issue'})
                  
        else:
            response.respond(400, {'message': "No (or invalid) action supplied"})
    else:
        response.respond(500, {'message': "No path_info supplied"})
