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
#
# votegroup
# A program for creating a list of voters in the given issue group
#
# o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
# o  creates a group directory (/home/voter/issues/group/),
#    and adds to it a "voters" file containing a list of e-mail addresses.
#
# Originally created by Roy Fielding
#
from collections import Counter
import os
import re
import subprocess
import sys
import argparse

import steve


def accept_or_exit():
  while True:
    answer = steve.get_input_line('"ok" to accept, or "abort" to exit', False)
    answer = answer.lower()
    if answer == 'abort':
      sys.exit(1)
    if answer == 'ok':
      return


def main():
  args = parse_argv()

  # Expand the set of arguments (as a side-effect), if they were not provided
  # on the cmdline.
  augment_args(args)

  voters = steve.get_group(args.file)
  if not voters:
    steve.die('No valid e-mail addresses were found in %s' % (args.file,))

  print 'Here is the list of voter e-mail addresses:'
  print '=============================================================='
  for voter in voters:
    print voter
  print '=============================================================='

  duplicates = len(voters) - len(set(voters))
  if duplicates:
    print 'Found duplicates:\n  %s' % '\n  '.join([x for x, y in Counter(voters).items() if y > 1])
    steve.die('%s duplicate voter%s must be removed from the list' % (duplicates, 's' if duplicates > 1 else ''))

  if not args.batch:
    accept_or_exit()

  diff_voters_file(args)

  create_voters_file(args)


def parse_argv():
  parser = argparse.ArgumentParser(
    prog=steve.PROG,
    description='Make an issue for managing an on-line, '
                'anonymous voting process',
  )
  parser.add_argument('-b', '--batch', action='store_true',
                      help='batch processing: assume "ok" unless errors')
  parser.add_argument('-g', '--group',
                      help='create an issue for an existing group of voters')
  parser.add_argument('-f', '--file',
                      help='contains the list of voter e-mail addresses, one per line')

  return parser.parse_args()


def augment_args(args):
  "Update ARGS in-place with missing values."

  if args.group is None:
    args.group = steve.get_input_line('group name for voters on this issue', True)
  if not re.match(r'^\w+$', args.group):
    steve.die('group name must be an alphanumeric token')

  if args.file is None:
    args.file = steve.get_input_line('file pathname voter e-mail addresses', True)
  args.file = os.path.realpath(args.file)
  if not os.path.exists(args.file):
    steve.die('info file does not exist: %s', args.file)
  if args.file.startswith('/etc/'):
    steve.die('forbidden to read info files from: /etc')
  if args.file.startswith(steve.ISSUE_DIR + os.path.sep):
    steve.die('forbidden to read info files from: %s', steve.ISSUE_DIR)


def _run_cmd(cmd, cwd=None):
  process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  (stdout, stderr) = process.communicate()

  return process.returncode, stdout + stderr


def diff_voters_file(args):
  VOTERS_FILE = os.path.join(steve.ISSUE_DIR, 'voters')
  VOTERS_FILE = os.path.join('.', 'voters')
  if os.path.exists(VOTERS_FILE):
    _, stdout = _run_cmd(['diff', '-u', VOTERS_FILE, args.file])

    print 'Differences from existing list of voters:'
    print '=============================================================='
    print stdout
    print '=============================================================='

    if not args.batch:
      accept_or_exit()

    _run_cmd(['mv', '-f', VOTERS_FILE, VOTERS_FILE + os.path.extsep + 'old'])


def create_voters_file(args):
  VOTERS_FILE = os.path.join(steve.ISSUE_DIR, 'voters')
  VOTERS_FILE = os.path.join('.', 'voters')

  _run_cmd(['cp', args.file, VOTERS_FILE])

  print '\n\n%s: %s' % (steve.hash_file(VOTERS_FILE), VOTERS_FILE)


if __name__ == '__main__':
  main()
