#!/usr/bin/env python
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

# Jump to parent dir for imports
import sys
import os.path
import ConfigParser as configparser
import argparse

parser = argparse.ArgumentParser(description='Command line options.')
parser.add_argument('--nodb', dest='nodb', action='store_true', 
                   help="Only perform library test, don't use any database")
args = parser.parse_args()


sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

# Fetch config
config = configparser.RawConfigParser()
config.read(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)) + '/steve.cfg')

# Some quick paths
homedir = config.get("general", "homedir")
if args.nodb:
    config.set("database", "disabled", "true")

from lib import response, voter, election, form, constants

crashed = 0
failed = 0
okay = 0

print("Testing vote types...")


# Validation functions inside vote types
for t in constants.VOTE_TYPES:
    sys.stdout.write("Testing %s's validation function with an invalid vote..." % t['key'])
    try:
        # All vote functions should reject this vote as invalid
        if t['validate_func']("blablabla", {'type': t['key'], 'candidates': ['candidate 1', 'candidate 2']}) != None:
            print("Okay")
            okay += 1
        else:
            print("Borked?")
            failed += 1
            
        # All except COP votes will accept this 'a' vote
        if t['key'].find("cop") == -1:
            sys.stdout.write("Testing %s's validation function with a valid vote..." % t['key'])
            if t['validate_func']("a", {'type': t['key'], 'candidates': ['candidate 1', 'candidate 2']}) == None:
                print("Okay")
                okay += 1
            else:
                print("Borked?")
                failed += 1
                
    except Exception as err:
        print("CRASHED: %s" % err)
        failed += 0
        
        
print("\n\n--------------------------")
print("%4u tests were successful" % okay)
print("%4u tests failed" % failed)
print("%4u tests crashed python" % crashed)
print("--------------------------")

if crashed > 0:
    sys.exit(-2)
if failed > 0:
    sys.exit(-1)
