#!/usr/bin/env/python
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
import os, sys, random, time

path = os.path.abspath(os.getcwd() + "/..")
sys.path.append(path)

version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
    
print("Reading steve.cfg")
config = configparser.RawConfigParser()
config.read('../steve.cfg')

homedir = config.get("general", "homedir")

from lib import election, voter, constants

print("Attempting to set up STeVe directories...")

if os.path.isdir(homedir):
    print("Creating election folder")
    if os.path.exists(homedir + "/issues"):
        print("Election folder already exists, nothing to do here..")
        sys.exit(-1)
    else:
        try:
            os.mkdir(homedir + "/issues")
            print("All done!")
        except Exception as err:
            print("Could not create dir: %s" % err)
else:
    print("Home dir (%s) does not exist, please create it!" % homedir)
    sys.exit(-1)