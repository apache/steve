#!/usr/bin/env python
#
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
#
#
# make_issue
#
# A program for creating issues to be voted upon by the named "group"
#
# o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
# o  creates an issue directory (/home/voter/issues/group/YYYYMMDD-name/),
#    and fills it with files for the issue info, election monitors,
#    and tally file;
#
# o  creates tables of hash-ids and hashed-hash-ids for use in validating
#    votes, verifying that the values are unique;
#
# o  mails to the vote monitors an alert message to start tallying;
#
# o  mails to each voter their hash-id to be used, issue number, and
#    some text explaining the issue.
#

import sys
import os
import argparse
import re
import shutil
import cStringIO

### how do we want to "properly" adjust path?
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))
import steve
import ezt


def main():
  args = parse_argv()

  ### where should we look for this config file?
  config = steve.load_config('steve.conf')

  # Expand the set of arguments (as a side-effect), if they were not provided
  # on the cmdline.
  augment_args(args, config)

  issue_name = '%s-%s-%s' % (args.group, args.start, args.issue)

  # Note: config.issue_dir updated as a side-effect
  voters = get_voters(args, config)

  # Note: config.issue_dir updated as a side-effect
  create_issue_dir(issue_name, args, config)

  info_fname = create_info_file(issue_name, args, config)
  monitors_hash, hash = build_hash(info_fname, voters, args)

  monitors_fname = create_monitors_file(args, config)
  type_fname = create_type_file(info_fname, args, config)
  verify_email(issue_name, info_fname, args, config)
  verify_voters(voters, args, config)

  email_monitors(issue_name, info_fname, monitors_hash, hash, args, config)
  email_voters()

  print "Issue %s with hashcode of %s\nhas been successfully created." \
        % (issue_name, monitors_hash)


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
  parser.add_argument('-s', '--start',
                      help='YYYYMMDD format of date that voting is allowed to start')
  parser.add_argument('-i', '--issue',
                      help='append this alphanumeric string to start date '
                           'as issue name')
  parser.add_argument('-f', '--file',
                      help='send the contents of this file to each voter '
                           'as explanation')
  parser.add_argument('-m', '--monitors',
                      help='e-mail address(es) for sending mail to vote monitor(s)')
  parser.add_argument('-v', '--votetype',
                      help='type of vote: yna = Yes/No/Abstain, '
                           'stvN = single transferable vote for [1-9] slots, '
                           'selectN = vote for [1-9] of the candidates')

  return parser.parse_args()


def augment_args(args, config):
  "Update ARGS in-place with missing values."

  if args.group is None:
    args.group = steve.get_input_line('group name for voters on this issue', True)
  if not re.match(r'^\w+$', args.group):
    steve.die('group name must be an alphanumeric token')

  if args.start is None:
    args.start = steve.get_input_line('YYYYMMDD date that voting starts', True)
  if not re.match(r'^[2-9]\d\d\d(0[1-9]|1[012])(0[1-9]|[12][0-9]|3[01])$',
                  args.start):
    steve.die('start date must be formatted as YYYYMMDD, like 20090930')

  if args.issue is None:
    args.issue = steve.get_input_line('short issue name to append to date', True)
  if not re.match(r'^\w+$', args.issue):
    steve.die('issue name must be an alphanumeric token')

  if args.file is None:
    args.file = steve.get_input_line('file pathname of issue info on %s'
                                     % (config.hostname,),
                                     True)
  args.file = os.path.realpath(args.file)
  if not os.path.exists(args.file):
    steve.die('info file does not exist: %s', args.file)
  if args.file.startswith('/etc/'):
    steve.die('forbidden to read info files from: /etc')
  issue_dir = os.path.realpath(config.issue_dir)
  if args.file.startswith(issue_dir + '/'):
    steve.die('forbidden to read info files from: %s', issue_dir)

  if args.monitors is None:
    args.monitors = steve.get_input_line('e-mail address(es) for vote monitors', True)
  if '@' not in args.monitors:
    steve.die('vote monitor must be an Internet e-mail address')

  if args.votetype is None:
    args.votetype = steve.get_input_line('vote type; yna, stvN, or selectN (N=1-9)',
                                         True)
  args.votetype = args.votetype.lower()
  if args.votetype == 'yna':
    args.selector = 0
    args.style = 'yes, no, or abstain'
  elif args.votetype.startswith('stv') and args.votetype[3:].isdigit():
    args.selector = int(args.votetype[3:])
    args.style = 'single transferable vote for %d slots' % (args.selector,)
  elif args.votetype.startswith('select') and args.votetype[6:].isdigit():
    args.selector = int(args.votetype[6:])
    args.style = 'select %d of the candidates labeled [a-z0-9]' % (args.selector,)
  else:
    steve.die('vote type must be yna, stvN, or selectN (N=[1-9])')


def get_voters(args, config):
  if not os.path.isdir(config.issue_dir):
    steve.die('cannot find: %s', config.issue_dir)

  config.issue_dir += '/' + args.group
  if not os.path.isdir(config.issue_dir):
    steve.die('group "%s" has not been created yet, see votegroup', args.group)
  if not os.access(config.issue_dir, os.R_OK | os.W_OK | os.X_OK):
    steve.die('you lack permissions on: %s', config.issue_dir)
  uid = os.stat(config.issue_dir).st_uid
  if uid != os.geteuid():
    steve.die('you are not the effective owner of: %s', config.issue_dir)

  voters = steve.get_group(config.issue_dir + '/voters')
  if not voters:
    steve.die('"%s" must be an existing voter group: see votegroup', args.group)

  return voters


def create_issue_dir(issue_name, args, config):
  print 'Creating new issue:', issue_name

  # Note that .issue_dir already has the group.
  config.issue_dir += '/%s-%s' % (args.start, args.issue)
  if os.path.exists(config.issue_dir):
    steve.die('already exists: %s', config.issue_dir)
  os.mkdir(config.issue_dir, 0700)


def create_info_file(issue_name, args, config):
  info_fname = config.issue_dir + '/issue'

  contents = _use_template('templates/info-header.ezt', None, issue_name,
                           None, None, None, args, config)
  open(info_fname, 'w').write(contents)

  return info_fname


def build_hash(info_fname, voters, args):
  while True:
    issue_id = steve.filestuff(info_fname)
    monitors_hash = steve.get_hash_of('%s:%s' % (issue_id, args.monitors))

    hash = { }
    for voter in voters:
      h1 = steve.get_hash_of('%s:%s' % (issue_id, voter))
      h2 = steve.get_hash_of('%s:%s' % (issue_id, h1))

      hash[voter] = (h1, h2)
      hash[h1] = (voter, None)
      hash[h2] = (voter, None)

    if len(hash) == 3 * len(voters):
      return monitors_hash, hash

    _ = steve.get_input_line('anything to retry collision-free hash', True)
    open(info_fname, 'a').write('')


def create_monitors_file(args, config):
  monitors_fname = config.issue_dir + '/monitors'

  open(monitors_fname, 'w').write(args.monitors + '\n')

  return monitors_fname


def create_type_file(info_fname, args, config):
  type_fname = config.issue_dir + '/vote_type'

  f = open(type_fname, 'w')
  f.write('%s\n' % (args.votetype,))

  if args.selector == 0:
    ballots = ('yes', 'no', 'abstain')
  else:
    ballots = steve.ballots(open(info_fname).readlines())

  f.writelines(option + '\n' for option in ballots)

  return type_fname


def verify_email(issue_name, info_fname, args, config):
  print 'Here is the issue information to be sent to each voter:'

  contents = open(info_fname).read() \
             + _use_template('templates/explain.ezt', 'unique-hash-key', issue_name,
                             None, None, None, args, config)
  _basic_verify(contents, args, config)


def verify_voters(voters, args, config):
  print 'Here is the list of voter e-mail addresses:'

  contents = '\n'.join(voters)
  _basic_verify(contents, args, config)


def _basic_verify(contents, args, config):
  print '=============================================================='
  print contents
  print '=============================================================='

  # No need to stop and verify.
  if args.batch:
    return

  while True:
    answer = steve.get_input_line('"ok" to accept, or "abort" to delete issue', False)
    answer = answer.lower()
    if answer == 'abort':
      shutil.rmtree(config.issue_dir)
      sys.exit(1)
    if answer == 'ok':
      return


def email_monitors(issue_name, info_fname, monitors_hash, hash, args, config):
  # Collect hash signatures of voter files that should not change
  ### need to expand this. allow some to be missing during dev/test.
  sigs = ['%s: %s' % (steve.hash_file('make_issue.py'), 'make_issue.py'),
          ]

  msg = _use_template('templates/monitor-email.ezt', 'unique-hash-key',
                      issue_name, monitors_hash, hash, sigs,
                      args, config)

  ### mail the result. for now, print out what would have been mailed.
  print '### DEBUG'
  print msg
  print '###'


def email_voters():
  pass


def _use_template(template_fname, key, issue_name, monitors_hash, hash, sigs,
                  args, config):
  data = {
    'hashid': key,
    'type': args.votetype.strip('0123456789'),
    'issue_name': issue_name,
    'group': args.group,
    'selector': args.selector,
    'style': args.style,
    'hostname': config.hostname,
    'monitors': args.monitors,
    'monitors_hash': monitors_hash,
    'email': config.email,
    'file': args.file,
    'sigs': sigs,
    }
  if hash:
    data['count'] = len(hash)
    data['hash2'] = sorted(v[1] for v in hash.values() if v[1])

  buf = cStringIO.StringIO()
  ezt.Template(template_fname, compress_whitespace=False).generate(buf, data)
  return buf.getvalue()


if __name__ == '__main__':
  os.umask(0077)
  main()
