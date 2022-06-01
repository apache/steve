#!/usr/bin/env python3
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

#
# The algorithms in this file are lifted from:
#   http://votesystem.cvs.sourceforge.net/viewvc/votesystem/votesystem/src/VoteMain.java?view=markup
# ... there is possibly some room for a "more Pythonic" approach. The
# conversion below was done in a straight-forward manner to ensure a
# true and correct algorithm conversion. The debug output precisely
# matches the output of VoteMain.java.
#

import sys
import os.path
import random
import argparse
import configparser
import re
import functools

ELECTED = 1
HOPEFUL = 2
ELIMINATED = 4
ALMOST = 8

ERROR_MARGIN = 0.00001
BILLIONTH = 0.000000001

RE_VOTE = re.compile(r'\[.{19}\]\s+'
                     r'(?P<voterhash>[\w\d]{32})\s+'
                     r'(?P<votes>[a-z]{1,26})',
                     re.I)

VERBOSE = False


def load_votes(fname):
  lines = open(fname).readlines()
  if lines[0].strip() == 'rank order':
    # The input file was processed by nstv-rank.py, or somehow otherwise
    # converted to the standard input for VoteMain.jar
    names = [s.strip() for s in lines[1].strip().split(',')][1:]
    labels = [s.strip() for s in lines[2].strip().split(',')][1:]
    assert len(names) == len(labels)
    remap = dict(zip(labels, names))

    votes = { }
    for line in lines[3:]:
      parts = line.strip().split(',')
      votes[parts[0]] = [remap[l] for l in parts[1:]]
    return names, votes

  # Let's assume we're looking at a raw_board_votes.txt file, and a
  # companion board_nominations.ini file.
  nominees = read_nominees(fname)

  votes = { }
  for line in lines:
    match = RE_VOTE.match(line)
    if match:
      # For a given voter hashcode, record their latest set of votes,
      # mapped from (character) labels to the nominee's name.
      votes[match.group('voterhash')] = [nominees[label]
                                         for label in match.group('votes')]

  # Map the nominee dictionary into a label-sorted list of names
  names = [nominees[label] for label in sorted(nominees)]

  return names, votes


def read_nominees(votefile):
  ini_fname = os.path.join(os.path.dirname(votefile),
                           'board_nominations.ini')

  # Use the below try instead to catch this??
  if not os.path.exists(ini_fname):
    print("Error: board_nominations.ini could not be found at " + ini_fname, file=sys.stderr)
    sys.exit(2)

  config = configparser.ConfigParser()
  config.read(ini_fname)
  try:
    return dict(config.items('nominees'))
  except:
    print("Error processing input file: " + ini_fname, file=sys.stderr)
    print(" Goodbye!", file=sys.stderr)
    sys.exit(2)


def run_vote(names, votes, num_seats):
  candidates = CandidateList(names)

  # name -> Candidate
  remap = dict((c.name, c) for c in candidates.l)

  # Turn VOTES into a list of ordered-lists of Candidate objects
  votes = [[remap[n] for n in choices] for choices in votes.values()]

  if candidates.count(ELECTED + HOPEFUL) <= num_seats:
    dbg('All candidates elected')
    candidates.change_state(HOPEFUL, ELECTED)
    return candidates
  if num_seats <= 0:
    candidates.change_state(HOPEFUL, ELIMINATED)
    return candidates

  quota = None  # not used on first pass
  iteration = 1
  while candidates.count(ELECTED) < num_seats:
    dbg('Iteration %d', iteration)
    iteration += 1
    quota = iterate_one(quota, votes, candidates, num_seats)
    candidates.reverse_random()

  dbg('All seats full')
  candidates.change_state(HOPEFUL, ELIMINATED)
  return candidates

  candidates.print_results()


class CandidateList(object):
  def __init__(self, names):
    num_cand = len(names)
    randset = generate_random(num_cand)

    self.l = [ ]
    for n, r in zip(names, randset):
      c = Candidate(n, r, num_cand-1)
      self.l.append(c)

  def count(self, state):
    count = 0
    for c in self.l:
      if (c.status & state) != 0:
        count += 1
    return count

  def change_state(self, from_state, to_state):
    any_changed = False
    for c in self.l:
      if (c.status & from_state) != 0:
        c.status = to_state
        if to_state == ELECTED:
          c.elect()
        elif to_state == ELIMINATED:
          c.eliminate()
        any_changed = True
    return any_changed

  def reverse_random(self):
    # Flip the values to create a different ordering among candidates. Note
    # that this will alternate the domain between [0.0, 1.0) and (0.0, 1.0]
    for c in self.l:
      c.rand = 1.0 - c.rand

  def adjust_weights(self, quota):
    for c in self.l:
      if c.status == ELECTED:
        c.adjust_weight(quota)

  def print_results(self):
    for c in self.l:
      print('%-40s%selected' % (c.name, c.status == ELECTED and ' ' or ' not '))

  def dbg_display_tables(self, excess):
    total = excess
    for c in self.l:
      dbg('%-20s %15.9f %15.9f', c.name, c.weight, c.vote)
      total += c.vote
    dbg('%-20s %15s %15.9f', 'Non-transferable', ' ', excess)
    dbg('%-20s %15s %15.9f', 'Total', ' ', total)

  def sorted(self):
    def compare(c1, c2):
      if c1.ahead < c2.ahead:
        return -1
      if c1.ahead == c2.ahead:
        ### expression for removed cmp() function
        return (c1.vote > c2.vote) - (c1.vote < c2.vote)
      return 1
    return sorted(self.l, key=functools.cmp_to_key(compare))

class Candidate(object):
  def __init__(self, name, rand, ahead):
    self.name = name
    self.rand = rand
    self.ahead = ahead
    self.status = HOPEFUL
    self.weight = 1.0
    self.vote = None  # calculated later

  def elect(self):
    self.status = ELECTED
    dbg('Elected: %s', self.name)

  def eliminate(self):
    self.status = ELIMINATED
    self.weight = 0.0
    dbg('Eliminated: %s', self.name)

  def adjust_weight(self, quota):
    assert quota is not None
    self.weight = (self.weight * quota) / self.vote

def iterate_one(quota, votes, candidates, num_seats):
  # assume that: count(ELECTED) < num_seats
  if candidates.count(ELECTED + HOPEFUL) <= num_seats:
    dbg('All remaining candidates elected')
    candidates.change_state(HOPEFUL, ELECTED)
    return None

  candidates.adjust_weights(quota)

  changed, new_quota, surplus = recalc(votes, candidates, num_seats)
  if not changed and surplus < ERROR_MARGIN:
    dbg('Remove Lowest (forced)')
    exclude_lowest(candidates.l)
  return new_quota


def recalc(votes, candidates, num_seats):
  excess = calc_totals(votes, candidates)
  calc_aheads(candidates)
  candidates.dbg_display_tables(excess)
  quota = calc_quota(len(votes), excess, num_seats)
  any_changed = elect(quota, candidates, num_seats)
  surplus = calc_surplus(quota, candidates)
  any_changed |= try_remove_lowest(surplus, candidates)
  return any_changed, quota, surplus


def calc_totals(votes, candidates):
  for c in candidates.l:
    c.vote = 0.0
  excess = 0.0
  for choices in votes:
    vote = 1.0
    for c in choices:
      if c.status == HOPEFUL:
        c.vote += vote
        vote = 0.0
        break
      if c.status != ELIMINATED:
        wv = c.weight * vote  # weighted vote
        c.vote += wv
        vote -= wv
        if vote == 0.0:  # nothing left to distribute
          break
    excess += vote
  return excess


def calc_aheads(candidates):
  c_sorted = candidates.sorted()
  last = 0
  for i in range(1, len(c_sorted)+1):
    if i == len(c_sorted) or c_sorted[last] != c_sorted[i]:
      for c in c_sorted[last:i]:
        c.ahead = (i - 1) + last
      last = i


def calc_quota(num_voters, excess, num_seats):
  if num_seats > 2:
    quota = (float(num_voters) - excess) / (float(num_seats + 1) + BILLIONTH)
  else:
    quota = (float(num_voters) - excess) /  float(num_seats + 1)
  if quota < ERROR_MARGIN:
    raise Exception('Internal Error - very low quota')
  dbg('Quota = %.9f', quota)
  return quota


def elect(quota, candidates, num_seats):
  for c in candidates.l:
    if c.status == HOPEFUL and c.vote >= quota:
      c.status = ALMOST

  any_changed = False

  while candidates.count(ELECTED + ALMOST) > num_seats:
    dbg('Vote tiebreaker! voters: %d  seats: %d',
        candidates.count(ELECTED + ALMOST), num_seats)
    candidates.change_state(HOPEFUL, ELIMINATED)
    exclude_lowest(candidates.l)
    any_changed = True  # we changed the candidates via exclude_lowest()

  any_changed |= candidates.change_state(ALMOST, ELECTED)
  return any_changed


def calc_surplus(quota, candidates):
  surplus = 0.0
  for c in candidates.l:
    if c.status == ELECTED:
      surplus += c.vote - quota
  dbg('Total Surplus = %.9f', surplus)
  return surplus


def try_remove_lowest(surplus, candidates):
  lowest1 = 1e18
  lowest2 = 1e18
  which = None
  for c in candidates.l:
    if c.status == HOPEFUL and c.vote < lowest1:
      lowest1 = c.vote
      which = c
  for c in candidates.l:
    if c.status != ELIMINATED and c.vote > lowest1 and c.vote < lowest2:
      lowest2 = c.vote

  diff = lowest2 - lowest1
  if diff >= 0.0:
    dbg('Lowest Difference = %.9f - %.9f = %.9f', lowest2, lowest1, diff)
  if diff > surplus:
    dbg('Remove Lowest (unforced)')
    which.eliminate()
    return True
  return False


def exclude_lowest(candidates):
  ### use: ahead = len(candidates) ??
  ahead = 1000000000.  # greater than any possible candidate.ahead
  rand = 1.1  # greater than any possible candidate.rand
  which = None
  used_rand = False

  for c in candidates:
    if c.status == HOPEFUL or c.status == ALMOST:
      if c.ahead < ahead:
        ahead = c.ahead
        rand = c.rand
        which = c
        use_rand = False
      elif c.ahead == ahead:
        use_rand = True
        if c.rand < rand:
          ran = c.rand
          which = c

  if use_rand:
    dbg('Random choice used!')

  assert which
  which.eliminate()


def generate_random(count):
  random.seed(0)  ### choose a seed based on input? for now: repeatable.
  while True:
    # Generate COUNT values in [0.0, 1.0)
    values = [random.random() for x in range(count)]

    # Ensure there are no duplicates
    for value in values:
      if values.count(value) > 1:
        break
    else:
      # The loop finished without breaking out
      return values


def dbg(fmt, *args):
  if VERBOSE:
    print(fmt % args)


def main(argv):
  parser = argparse.ArgumentParser(description="Calculate a winner for a vote")
  parser.add_argument('raw_file')
  parser.add_argument("-s", "--seats", dest="seats", type=int,
                      help="Number of seats available, default 9",
                      default=9)
  parser.add_argument("-v", "--verbose", dest="verbose", action="store_true",
                      help="Enable verbose logging", default=False)

  args = parser.parse_args(argv)

  global VERBOSE
  VERBOSE = args.verbose

  votefile = args.raw_file
  num_seats = args.seats

  if not os.path.exists(votefile):
    parser.print_help()
    sys.exit(1)

  names, votes = load_votes(votefile)

  candidates = run_vote(names, votes, num_seats)
  candidates.print_results()
  print('Done!')


if __name__ == '__main__':
  main(sys.argv[1:])
