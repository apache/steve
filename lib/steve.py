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
#
# steve.py -- shared code for Apache Steve
#

import sys
import os

SCRIPT = os.path.basename(sys.argv[0])


def get_input_line(prompt, quittable=False):
  "Prompt and fetch a line of input."

  if quittable:
    prompt += ' (q=quit)'
  prompt += ': '
  while True:
    line = raw_input(prompt).strip()
    if quittable and line == 'q':
      sys.exit(0)
    if line:
      return line
    # loop until we get an answer


def get_group(fname):
  "Return the group of voters, as a set of email addresses."

  group = set()
  for line in open(fname).readlines():
    i = line.find('#')
    if i >= 0:
      line = line[:i]
    line = line.strip()
    if not line:
      continue
    if '@' not in line:
      print '%s: voter must be an Internet e-mail address.' % (SCRIPT,)
      sys.exit(1)
    group.add(line)

  return group
