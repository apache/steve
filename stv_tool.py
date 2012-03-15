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

#
# The algorithms in this file are lifted from:
#   http://votesystem.cvs.sourceforge.net/viewvc/votesystem/votesystem/src/VoteMain.java?view=markup
#

import random

ELECTED = 1
HOPEFUL = 2
ELIMINATED = 4
ALMOST = 8

ERROR_MARGIN = 0.00001
BILLIONTH = 0.000000001


def load_votes(fname):
  lines = open(fname).readlines()
  names = [s.strip() for s in lines[1].strip().split(',')][1:]
  labels = [s.strip() for s in lines[2].strip().split(',')][1:]
  assert len(names) == len(labels)
  remap = dict(zip(labels, names))

  votes = { }
  for line in lines[3:]:
    parts = line.strip().split(',')
    votes[parts[0]] = [remap[l] for l in parts[1:]]
  return names, votes


def run_vote(names, votes, num_seats):
  num_cand = len(names)
  randset = generate_random(num_cand)

  remap = { }  # name -> Candidate
  candidates = [ ]
  for n, r in zip(names, randset):
    c = Candidate(n, r, num_cand-1)
    remap[n] = c
    candidates.append(c)

  for choices in votes.values():
    for i in range(len(choices)):
      choices[i] = remap[choices[i]]

  if count_state(candidates, ELECTED + HOPEFUL) <= num_seats:
    dbg('All candidates elected')
    change_state(candidates, HOPEFUL, ELECTED)
    return
  if num_seats <= 0:
    change_state(candidates, HOPEFUL, ELIMINATED)
    return

  quota = None  # not used on first pass
  iteration = 1
  while count_state(candidates, ELECTED) < num_seats:
    dbg('Iteration %d', iteration)
    iteration += 1
    quota = iterate_one(quota, votes, candidates, num_seats)
    reverse_random(candidates)

  dbg('All seats full')
  change_state(candidates, HOPEFUL, ELIMINATED)

  for c in candidates:
    print '%-40s%selected' % (c.name, c.status == ELECTED and ' ' or ' not ')

  
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
  if count_state(candidates, ELECTED + HOPEFUL) <= num_seats:
    dbg('All remaining candidates elected')
    change_state(HOPEFUL, ELECTED)
    return None

  changed, new_quota, surplus = converge_one(quota, votes, candidates,
                                             num_seats)
  if not changed and surplus < ERROR_MARGIN:
    dbg('Remove Lowest (forced)')
    exclude_lowest(candidates)
  return new_quota


def converge_one(quota, votes, candidates, num_seats):
  for c in candidates:
    if c.status == ELECTED:
      c.adjust_weight(quota)
  return recalc(votes, candidates, num_seats)


def recalc(votes, candidates, num_seats):
  any_changed = False
  excess = calc_totals(votes, candidates)
  calc_aheads(candidates)
  ### if debug:
  display_tables(excess, candidates)
  quota = calc_quota(len(votes), excess, num_seats)
  elect(quota, candidates, num_seats)
  surplus = calc_surplus(quota, candidates)
  any_changed |= try_remove_lowest(surplus, candidates)
  return any_changed, quota, surplus


def calc_totals(votes, candidates):
  for c in candidates:
    c.vote = 0.0
  excess = 0.0
  for choices in votes.values():
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
  def compare_candidates(c1, c2):
    if c1.ahead < c2.ahead:
      return -1
    if c1.ahead == c2.ahead:
      return cmp(c1.vote, c2.vote)
    return 1

  c_sorted = sorted(candidates, compare_candidates)
  last = 0
  for i in range(1, len(c_sorted)+1):
    if i == len(c_sorted) \
          or compare_candidates(c_sorted[last], c_sorted[i]) != 0:
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
  for c in candidates:
    if c.status == HOPEFUL and c.vote >= quota:
      c.status = ALMOST

  any_changed = False

  while count_state(candidates, ELECTED + ALMOST) > num_seats:
    dbg('Vote tiebreaker! voters: %d  seats: %d',
        count_state(ELECTED + ALMOST), num_seats)
    change_state(candidates, HOPEFUL, ELIMINATED)
    exclude_lowest(candidates)
    any_changed = True  # we changed the candidates via exclude_lowest()

  any_changed |= change_state(candidates, ALMOST, ELECTED)
  return any_changed


def calc_surplus(quota, candidates):
  surplus = 0.0
  for c in candidates:
    if c.status == ELECTED:
      surplus += c.vote - quota
  dbg('Total Surplus = %.9f', surplus)
  return surplus


def try_remove_lowest(surplus, candidates):
  lowest1 = 1e18
  lowest2 = 1e18
  which = None
  for c in candidates:
    if c.status == HOPEFUL and c.vote < lowest1:
      lowest1 = c.vote
      which = c
  for c in candidates:
    if c != which and c.status != ELIMINATED and c.vote < lowest2:
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

  for c in candiates:
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


def count_state(candidates, state):
  count = 0
  for c in candidates:
    if (c.status & state) != 0:
      count += 1
  return count


def change_state(candidates, from_state, to_state):
  any_changed = False
  for c in candidates:
    if (c.status & from_state) != 0:
      c.status = to_state
      if to_state == ELECTED:
        c.elect()
      elif to_state == ELIMINATED:
        c.eliminate()
      any_changed = True
  return any_changed


def generate_random(count):
  random.seed(0)  ### choose a seed based on input?
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


def reverse_random(candidates):
  # Flip the values to create a different ordering among candidates. Note
  # that this will alternate the domain between [0.0, 1.0) and (0.0, 1.0]
  for c in candidates:
    c.rand = 1.0 - c.rand


def dbg(fmt, *args):
  print fmt % args


def display_tables(excess, candidates):
  total = excess
  for c in candidates:
    dbg('%-20s %15.9f %15.9f', c.name, c.weight, c.vote)
    total += c.vote
  dbg('%-20s %15s %15.9f', 'Non-transferable', ' ', excess)
  dbg('%-20s %15s %15.9f', 'Total', ' ', total)


if __name__ == '__main__':
  ### use cmdline params...
  names, votes = load_votes('/tmp/votes')
  run_vote(names, votes, 9)
  print 'Done!'
