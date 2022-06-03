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


#@deprecated
def load_votes(fname):
  line = open(fname).readline()
  if line.strip() == 'rank order':
    lines = open(fname).readlines()

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

  ini_fname = os.path.join(os.path.dirname(fname),
                           'board_nominations.ini')
  labelmap = read_labelmap(ini_fname)

  # Construct a label-sorted list of names from the labelmap.
  names = [name for _, name in sorted(labelmap.items())]

  # Load the raw votes that were recorded.
  votes_by_label = read_votefile(fname)

  # Remap all labels to names in the votes.
  # NOTE: v represents the voter hash. (### why return this?)
  votes = dict((v, [labelmap[l] for l in vote])
               for v, vote in votes_by_label.items())

  return names, votes


def read_votefile(fname):
  votes = { }
  for line in open(fname).readlines():
    match = RE_VOTE.match(line)
    if match:
      # For a given voter hashcode, record their latest set of votes.
      votes[match.group('voterhash')] = match.group('votes')

  ### we should discard voterhash, and just return .values()
  return votes


#@deprecated
def read_nominees(votefile):
  ini_fname = os.path.join(os.path.dirname(votefile),
                           'board_nominations.ini')
  return read_labelmap(ini_fname)


def read_labelmap(fname):
  if not os.path.exists(fname):
    print(f'ERROR: "{fname}" could not be found.', file=sys.stderr)
    sys.exit(2)

  config = configparser.ConfigParser()
  config.read(fname)
  try:
    return dict(config.items('nominees'))
  except:
    print(f'ERROR: could not process input file, "{fname}".', file=sys.stderr)
    sys.exit(2)


#@deprecated
def run_vote(names, votes, num_seats):

  # List of votestrings, each as a list of ordered name choices.
  ordered_votes = votes.values()

  return run_stv(names, ordered_votes, num_seats)


def run_stv(names: list, ordered_votes: list, num_seats: int):

  # NOTE: NAMES must be a list for repeatability purposes. It does not
  # need to obey any particular ordering rules, but when re-running
  # tallies, NAMES must be presented with the same ordering.

  assert len(set(names)) == len(names), "duplicates present!"
  assert num_seats > 0

  candidates = CandidateList(names)

  # name -> Candidate
  remap = dict((c.name, c) for c in candidates.l)

  # We can test that ordering of voters has no bearing. Perform runs
  # and alter the .seed() value.
  #ordered_votes = list(ordered_votes); random.seed(1); random.shuffle(ordered_votes); print('VOTE:', ordered_votes[0])

  # VOTES is a list of ordered-lists of Candidate objects
  votes = [[remap[n] for n in choices] for choices in ordered_votes]

  if candidates.count(ELECTED + HOPEFUL) <= num_seats:
    dbg('All candidates elected')
    candidates.change_state(HOPEFUL, ELECTED)
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


class CandidateList(object):
  def __init__(self, names):
    num_cand = len(names)
    randset = generate_random(num_cand)
    #dbg('RANDSET: %s', randset)

    self.l = [ ]
    for n, r in zip(names, randset):
      c = Candidate(n, r, num_cand-1)
      self.l.append(c)

  def count(self, state):
    return sum(int((c.status & state) != 0) for c in self.l)

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

  def calc_aheads(self):
    def compare(c1, c2):
      if c1.ahead < c2.ahead:
        return -1
      if c1.ahead == c2.ahead:
        ### expression for removed cmp() function
        return (c1.vote > c2.vote) - (c1.vote < c2.vote)
      return 1

    ### the algorithm below seems very obtuse, to produce very little
    ### change. It alters .ahead on the first iteration, then does
    ### minor tweaks afterwards. And it seems to only work pair-wise.
    ### It feels this could be simplified.
    ### refer to STV.java::calcAheads()
    c_sorted = sorted(self.l, key=functools.cmp_to_key(compare))
    last = 0
    for i in range(1, len(c_sorted)+1):
      if i == len(c_sorted) or c_sorted[last].vote != c_sorted[i].vote:
        for c in c_sorted[last:i]:
          c.ahead = (i - 1) + last
        last = i

  def apply_votes(self, votes):
    # Reset each candidates vote 0.0
    for c in self.l:
      c.vote = 0.0

    # Each voter has 1 vote. Due to candidate weighting, it might not
    # get fully-assigned to candidates. We need to remember this excess.
    excess = 0.0

    # Now, process that 1 vote.
    for choices in votes:
      vote = 1.0

      # Distribute the vote, according to their ordered wishes.
      for c in choices:
        if c.status == HOPEFUL:
          c.vote += vote
          vote = 0.0
          break
        if c.status != ELIMINATED:
          wv = c.weight * vote  # weighted vote
          c.vote += wv
          vote -= wv
          # Note: should probably test for floating point margins, but
          # it's fine to just let this spill into the EXCESS value.
          if vote == 0.0:  # nothing left to distribute
            break
      excess += vote

    # Done. Tell caller what we could not distribute.
    return excess


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
  excess = candidates.apply_votes(votes)
  a1 = [c.ahead for c in candidates.l]
  candidates.calc_aheads()
  a2 = [c.ahead for c in candidates.l]
  if a1 != a2:
    pass #print(f'CHANGE:\n  {a1}\n  {a2}')
  candidates.dbg_display_tables(excess)
  quota = calc_quota(len(votes), excess, num_seats)
  any_changed = elect(quota, candidates, num_seats)
  surplus = calc_surplus(quota, candidates)
  any_changed |= try_remove_lowest(surplus, candidates)
  return any_changed, quota, surplus


#@deprecated
def calc_totals(votes, candidates):
  return candidates.apply_votes(votes)


#@deprecated
def calc_aheads(candidates):
  candidates.calc_aheads()


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
  surplus = sum(c.vote - quota for c in candidates.l if c.status == ELECTED)
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
  which = None
  use_rand = False

  for c in candidates:
    if c.status == HOPEFUL or c.status == ALMOST:
      if which is None or c.ahead < which.ahead:
        which = c
        use_rand = False
      elif c.ahead == which.ahead:
        use_rand = True
        if c.rand < which.rand:
          which = c

  if use_rand:
    dbg('Random choice used!')

  assert which
  which.eliminate()


def generate_random(count):
  random.seed(0)  ### choose a seed based on input? for now: repeatable.
  while True:
    # Generate COUNT values in [0.0, 1.0)
    # NOTE: use a list (not a set or dict) for repeatable ordering.
    values = [random.random() for x in range(count)]

    # Use a set() to check for dups. If no dups, then return the values.
    if len(set(values)) == count:
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

  if not os.path.exists(args.raw_file):
    parser.print_help()
    sys.exit(1)

  ini_fname = os.path.join(os.path.dirname(args.raw_file),
                           'board_nominations.ini')
  labelmap = read_labelmap(ini_fname)
  # Construct a label-sorted list of names from the labelmap.
  names = [name for _, name in sorted(labelmap.items())]

  # Turn votes using labels into by-name.
  votes_by_label = read_votefile(args.raw_file).values()
  votes = [[labelmap[l] for l in vote] for vote in votes_by_label]

  candidates = run_stv(names, votes, args.seats)
  candidates.print_results()
  print('Done!')


if __name__ == '__main__':
  main(sys.argv[1:])
