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

path = os.path.abspath(os.getcwd())

sys.path.append(path)
sys.path.append(os.path.basename(sys.argv[0]))
if 'SCRIPT_FILENAME' in os.environ:
    sys.path.insert(0, os.path.basename(os.environ['SCRIPT_FILENAME']))
    
from lib import response


# Fetch config (hack, hack, hack)
config = configparser.RawConfigParser()
config.read(path + '/../../steve.cfg')

# Some quick paths
homedir = config.get("general", "homedir")
pathinfo = os.environ['PATH_INFO'] if 'PATH_INFO' in os.environ else None
form = cgi.FieldStorage();



# TODO: Authentication goes here
karma = 5 # assume admin karma for now

# Figure out what to do and where
if pathinfo:
    l = pathinfo.split("/")
    if l[0] == "":
        l.pop(0)
    action = l[0]
    election = l[1] if len(l) > 1 else None


    # Set up new election?
    if action == "setup":
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
                                'ends': form.getvalue('ends')
                            }))
                            f.close()
                        response.respond(201, {'message': 'Created!'})
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
                            response.respond(201, {'message': 'Created!'})
                        except Exception as err:
                            response.respond(500, {'message': "Could not create issue: %s" % err})
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
    else:
        response.respond(400, {'message': "No (or invalid) action supplied"})
else:
    response.respond(500, {'message': "No path_info supplied"})
