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
form = cgi.FieldStorage();

whoami = os.environ['REMOTE_USER'] if 'REMOTE_USER' in os.environ else None

from lib import response, voter, election

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
        election = l[1] if len(l) > 1 else None
 
        # List all existing/previous elections?
        if action == "list":
            output = []
            errors = []
            path = os.path.join(homedir, "issues")
            elections = [ f for f in listdir(path) if os.path.isdir(os.path.join(path,f))]
            for election in elections:
                try:
                    elpath = os.path.join(homedir, "issues", election)
                    with open(elpath + "/basedata.json", "r") as f:
                        basedata = json.loads(f.read())
                        f.close()
                        if 'hash' in basedata:
                            del basedata['hash']
                        basedata['id'] = election
                        if karma >= 5 or ('owner' in basedata and basedata['owner'] == whoami):
                            output.append(basedata)
                except Exception as err:
                    errors.append("Could not parse election '%s': %s" % (election, err))
            if len(errors) > 0:
                response.respond(206, { 'elections': output, 'errors': errors})
            else:
                response.respond(200, { 'elections': output})
        # Set up new election?
        elif action == "setup":
            if karma >= 5: # karma of 5 required to set up an election base
                if election:
                    if os.path.isdir(os.path.join(homedir, "issues", election)):
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
                            elpath = os.path.join(homedir, "issues", election)
                            os.mkdir(elpath)
                            with open(elpath  + "/basedata.json", "w") as f:
                                f.write(json.dumps({
                                    'title': form.getvalue('title'),
                                    'owner': form.getvalue('owner'),
                                    'monitors': form.getvalue('monitors').split(","),
                                    'starts': form.getvalue('starts'),
                                    'ends': form.getvalue('ends'),
                                    'hash': hashlib.sha512("%f-stv-%s" % (time.time(), os.environ['REMOTE_ADDR'])).hexdigest(),
                                    'open': form.getvalue('open')
                                }))
                                f.close()
                            response.respond(201, {'message': 'Created!', 'id': election})
                        except Exception as err:
                            response.respond(500, {'message': "Could not create election: %s" % err})
                else:
                    response.respond(400, {'message': "No election name specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
                
        # Create an issue in an election
        elif action == "create":
            if karma >= 4: # karma of 4 required to set up an issue for the election
                if election:
                    issue = l[2] if len(l) > 2 else None
                    if not issue:
                        response.respond(400, {'message': 'No issue ID specified'})
                    else:
                        issuepath = os.path.join(homedir, "issues", election, issue)
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
                                valid_types = ['yna','stv1','stv2','stv3','stv4','stv5','stv6','stv7','stv8','stv9']
                                if not form.getvalue('type') in valid_types:
                                    raise Exception('Invalid vote type: %s' % form.getvalue('type'))
                                with open(issuepath + ".json", "w") as f:
                                    candidates = []
                                    if form.getvalue('candidates'):
                                        for name in form.getvalue('candidates').split("\n"):
                                            candidates.append({'name': name})
                                    f.write(json.dumps({
                                        'title': form.getvalue('title'),
                                        'description': form.getvalue('description'),
                                        'type': form.getvalue('type'),
                                        'candidates': candidates,
                                        'seconds': form.getvalue('seconds'),
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
                if election:
                    issue = l[2] if len(l) > 2 else None
                    if not issue:
                        response.respond(400, {'message': 'No issue ID specified'})
                    else:
                        issuepath = os.path.join(homedir, "issues", election, issue)
                        if os.path.isfile(issuepath + ".json"):
                            try:
                                os.unlink(issuepath + ".json")
                                response.respond(200, {'message': "Issue deleted"})
                            except Exception as err:
                                response.respond(500, {'message': 'Could not delete issue: %s' % err})
                        else:
                            response.respond(404, {'message': "No such issue!"})
                else:
                    response.respond(400, {'message': "No election specified!"})
            else:
                response.respond(403, {'message': 'You do not have enough karma for this'})
        
        
        
        # Edit an issue or election
        elif action == "edit":
            issue = l[2] if len(l) > 2 else None
            if (issue and karma >= 4) or (karma >= 5 and election):
                if election:
                    if not issue:
                        elpath = os.path.join(homedir, "issues", election)
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
                                            val = val.split(",")
                                        js[field] = val
                                with open(elpath + "/basedata.json", "w") as f:
                                    f.write(json.dumps(js))
                                    f.close()
                                response.respond(200, {'message': "Changed saved"})
                            except Exception as err:
                                response.respond(500, {'message': "Could not edit election: %s" % err})
                    else:
                        issuepath = os.path.join(homedir, "issues", election, issue)
                        if not os.path.isfile(issuepath + ".json"):
                            response.respond(404, {'message': 'No such issue'})
                        else:
                            try:
                                js = {}
                                with open(issuepath + ".json", "r") as f:
                                    js = json.loads(f.read())
                                    f.close()
                                fields = ['title','description','type','candidates','seconds','nominatedby']
                                for field in fields:
                                    val = form.getvalue(field)
                                    if val:
                                        if field == "candidates" or field == "seconds":
                                            xval = val.split("\n")
                                            val = []
                                            for entry in xval:
                                                val.append({'name': entry})
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
                issuepath = os.path.join(homedir, "issues", election, issue)
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
                issuepath = os.path.join(homedir, "issues", election, issue)
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
                issuepath = os.path.join(homedir, "issues", election, issue)
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
            if election:
                js = []
                elpath = os.path.join(homedir, "issues", election)
                if os.path.isdir(elpath):
                    basedata = {}
                    try:
                        with open(elpath + "/basedata.json", "r") as f:
                            basedata = json.loads(f.read())
                            f.close()
                        issues = [ f for f in listdir(elpath) if os.path.isfile(os.path.join(elpath,f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
                        for issue in issues:
                            try:
                                with open(elpath + "/" + issue, "r") as f:
                                    entry = json.loads(f.read())
                                    f.close()
                                    entry['id'] = issue.strip(".json")
                                    entry['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (os.environ['SERVER_NAME'], election, issue.strip(".json"))
                                    entry['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (os.environ['SERVER_NAME'], election, issue.strip(".json"))
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
            else:
                    response.respond(404, {'message': 'No such election'})
        elif action == "invite" and karma >= 3:
            # invite one or more people to an election
            if election:
                email = form.getvalue('email')
                msgtype = form.getvalue('msgtype')
                msgtemplate = form.getvalue('msgtemplate')
                if not email or len(email) > 300 or not re.match(r"([^@]+@[^@]+)", email):
                    response.respond(400, {'message': 'Could not request voter ID: Invalid email address specified'})
                elif not msgtemplate or len(msgtemplate) < 10:
                    response.respond(400, {'message': 'No message template specified'})
                else:
                    js = []
                    elpath = os.path.join(homedir, "issues", election)
                    if os.path.isdir(elpath):
                        basedata = {}
                        try:
                            with open(elpath + "/basedata.json", "r") as f:
                                basedata = json.loads(f.read())
                                f.close()
                            if (not 'open' in basedata or basedata['open'] != "true") and msgtype == "open":
                                raise Exception("An open vote invite was requested, but this election is not public")
                            if msgtype != "open":
                                voterid, xhash = voter.add(election, basedata, email)
                                message = msgtemplate.replace("$votelink", "%s/election.html?%s/%s" % (config.get("general", "rooturl"), election, voterid))
                                message = message.replace("$title", basedata['title'])
                                subject = "Election open for votes: %s (%s)" % (election, basedata['title'])
                                voter.email(email, subject, message)
                            else:
                                message = msgtemplate.replace("$votelink", "%s/request_link.html?%s" % (config.get("general", "rooturl"), election))
                                message = message.replace("$title", basedata['title'])
                                subject = "Public election open for votes: %s (%s)" % (election, basedata['title'])
                                voter.email(email, subject, message)
                            response.respond(200, {'message': "Vote link sent"})
                        except Exception as err:
                            response.respond(500, {'message': 'Could not load base data: %s' % err})
                        
                        response.respond(200, {'message': "Vote link sent to %s" % email})
                    else:
                        response.respond(404, {'message': 'No such election'})
            else:
                    response.respond(404, {'message': 'No such election'})
                    
        else:
            response.respond(400, {'message': "No (or invalid) action supplied"})
    else:
        response.respond(500, {'message': "No path_info supplied"})
