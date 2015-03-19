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
    issue = l[2]  if len(l) > 2 else None
    voterid = l[3] if len(l) > 3 else None
    
    if action == "view":
        # View a list of issues for an election
        if election and not issue:
            js = []
            elpath = os.path.join(homedir, "issues", election)
            if os.path.isdir(elpath):
                basedata = {}
                try:
                    with open(elpath + "/basedata.json", "r") as f:
                        basedata = json.loads(f.read())
                        if 'hash' in basedata:
                            del basedata['hash']
                        f.close()
                    issues = [ f for f in listdir(elpath) if os.path.isfile(os.path.join(elpath,f)) and f != "basedata.json" ]
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
                response.respond(200, {'base_data': basedata, 'issues': js, 'baseurl': "https://%s/steve/election?%s" % (os.environ['SERVER_NAME'], election)})
            else:
                response.respond(404, {'message': 'No such election'})
                
        # View a speficic issue
        elif election and issue:
            js = []
            issuepath = os.path.join(homedir, "issues", election, issue)
            if os.path.isfile(issuepath + ".json"):
                try:
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
    elif action == "vote":
        response.respond(500, {'message': 'Not implemented yet'})
    else:
        response.respond(400, {'message': 'Invalid action supplied'})
else:
    response.respond(500, {'message': 'No path info supplied, aborting'})