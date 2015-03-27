#!/usr/bin/env python
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
""" Tallying program for pySTeVe """
import sys, re, json, os

version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
from os import listdir
from os.path import isdir, isfile
path = os.path.abspath(os.getcwd() + "/../") # Get parent dir, so we can snag 'lib' from there

sys.path.append(path)
sys.path.append(os.path.basename(sys.argv[0]))

# Fetch config (hack, hack, hack)
config = configparser.RawConfigParser()
config.read(path + '/steve.cfg')

# Some quick paths
homedir = config.get("general", "homedir")

# Import the goodness
from lib import response, voter, election, form, constants



import argparse

parser = argparse.ArgumentParser(description='Command line options.')
parser.add_argument('-e', '--election', dest='election', type=str, help='Election to load')
parser.add_argument('-i', '--issue', dest='issue', type=str, help='Issue to load')
parser.add_argument('-f', '--file', dest='vfile', type=str, help='Monitor file to load. Used by monitors instead of specifying election and issue')
parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", help="Enable verbose logging", default=False)
args = parser.parse_args()

baseData = None
issueData = None
votes = None

if args.election and args.issue:
    issueData = election.getIssue(args.election, args.issue)
    baseData = election.getBasedata(args.election)
    votes = election.getVotes(args.election, args.issue)
elif args.vfile:
    with open(args.vfile, "r") as f:
        js = json.loads(f.read())
        f.close()
    issueData = js['issue']
    baseData = js['base']
    votes = js['votes']
else:
    parser.print_help()
            

if baseData and issueData:
    if not votes or len(votes) == 0:
        print("No votes have been cast yet, cannot tally")
        sys.exit(-1)
    else:
        tally, prettyprint = election.tally(votes, issueData)
        if args.verbose and tally.get('debug'):
            print("------\nDebug:\n------")
            for line in tally['debug']:
                print(line)
        print("----------")
        print("Base data:")
        print("----------")
        print("Election:   %s" % baseData['title'])
        print("Issue:      %s" % issueData['title'])
        print("Votes cast: %u" % len(votes))
        print("\n-----------------\nElection results:\n-----------------")
        print(prettyprint)
else:
    print("No such election or issue!")
    sys.exit(-1)