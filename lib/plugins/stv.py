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
""" STV Voting Plugin """
import re, json, random

ELECTED = 1
HOPEFUL = 2
ELIMINATED = 4
ALMOST = 8

ERROR_MARGIN = 0.00001
BILLIONTH = 0.000000001


from lib import constants

debug = []

def validateSTV(vote, issue):
    "Tries to validate a vote, returns why if not valid, None otherwise"
    letters = [chr(i) for i in range(ord('a'), ord('a') + len(issue['candidates']))]
    for char in letters:
        if vote.count(char) > 1:
            return "Duplicate letters found"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None


def run_vote(names, votes, num_seats):
  candidates = CandidateList(names)

  # name -> Candidate
  remap = dict((c.name, c) for c in candidates.l)

  # Turn VOTES into a list of ordered-lists of Candidate objects
  votes = [[remap[n] for n in choices] for choices in votes.values()]

  if candidates.count(ELECTED + HOPEFUL) <= num_seats:
    debug.append('All candidates elected')
    candidates.change_state(HOPEFUL, ELECTED)
    return
  if num_seats <= 0:
    candidates.change_state(HOPEFUL, ELIMINATED)
    return

  quota = None  # not used on first pass
  iteration = 1
  while candidates.count(ELECTED) < num_seats:
    debug.append('Iteration %d' % iteration)
    iteration += 1
    quota = iterate_one(quota, votes, candidates, num_seats)
    candidates.reverse_random()

  debug.append('All seats full')
  candidates.change_state(HOPEFUL, ELIMINATED)

  return candidates.retval()


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
  def retval(self):
    winners = []
    for c in self.l:
        if c.status == ELECTED:
            winners.append(c.name)
    return winners
            
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
      print '%-40s%selected' % (c.name, c.status == ELECTED and ' ' or ' not ')

  def dbg_display_tables(self, excess):
    total = excess
    for c in self.l:
      debug.append('%-20s %15.9f %15.9f' % (c.name, c.weight, c.vote))
      total += c.vote
    debug.append('%-20s %15s %15.9f' %( 'Non-transferable', ' ', excess))
    debug.append('%-20s %15s %15.9f' % ( 'Total', ' ', total))


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
    debug.append('Elected: %s' % self.name)

  def eliminate(self):
    self.status = ELIMINATED
    self.weight = 0.0
    debug.append('Eliminated: %s' % self.name)

  def adjust_weight(self, quota):
    assert quota is not None
    self.weight = (self.weight * quota) / self.vote

  def __cmp__(self, other):
    if self.ahead < other.ahead:
      return -1
    if self.ahead == other.ahead:
      return cmp(self.vote, other.vote)
    return 1


def iterate_one(quota, votes, candidates, num_seats):
  # assume that: count(ELECTED) < num_seats
  if candidates.count(ELECTED + HOPEFUL) <= num_seats:
    debug.append('All remaining candidates elected')
    candidates.change_state(HOPEFUL, ELECTED)
    return None

  candidates.adjust_weights(quota)

  changed, new_quota, surplus = recalc(votes, candidates, num_seats)
  if not changed and surplus < ERROR_MARGIN:
    debug.append('Remove Lowest (forced)')
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
  c_sorted = sorted(candidates.l)
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
  debug.append('Quota = %.9f' % quota)
  return quota


def elect(quota, candidates, num_seats):
  for c in candidates.l:
    if c.status == HOPEFUL and c.vote >= quota:
      c.status = ALMOST

  any_changed = False

  while candidates.count(ELECTED + ALMOST) > num_seats:
    debug.append('Vote tiebreaker! voters: %d  seats: %d' %(        candidates.count(ELECTED + ALMOST), num_seats))
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
  debug.append('Total Surplus = %.9f' % surplus)
  return surplus


def try_remove_lowest(surplus, candidates):
  lowest1 = 1e18
  lowest2 = 1e18
  which = None
  for c in candidates.l:
    if c.status == HOPEFUL and c.vote < lowest1:
      lowest1 = c.vote
      which = c
  if not which:
    debug.append("Could not find a subject to eliminate")
    return False
  for c in candidates.l:
    if c != which and c.status != ELIMINATED and c.vote < lowest2:
      lowest2 = c.vote

  diff = lowest2 - lowest1
  if diff >= 0.0:
    debug.append('Lowest Difference = %.9f - %.9f = %.9f' % ( lowest2, lowest1, diff))
  if diff > surplus:
    debug.append('Remove Lowest (unforced)')
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
    debug.append('Random choice used!')

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


def tallySTV(votes, issue):
    
    m = re.match(r"stv(\d+)", issue['type'])
    if not m:
        raise Exception("Not an STV vote!")
    
    numseats = int(m.group(1))
    candidates = {}
    z = 0
    for c in issue['candidates']:
        candidates[chr(ord('a') + z)] = c['name']
        z += 1

    # run the stv calc
    winners = run_vote(candidates, votes, numseats)
    winnernames = []
    
    for c in winners:
        winnernames.append(candidates[c])

    # Return the data
    return {
        'votes': len(votes),
        'winners': winners,
        'winnernames': winnernames,
        'debug': debug
    }, """
Winners:
 - %s
""" % "\n - ".join(winnernames)


constants.appendVote (
    {
        'key': "stv1",
        'description': "Single Transferable Vote with 1 seat",
        'category': 'stv',
        'validate_func': validateSTV,
        'vote_func': None,
        'tally_func': tallySTV
    },
)

# Add ad nauseam
for i in range(2,constants.MAX_NUM+1):
    constants.appendVote (
        {
            'key': "stv%u" % i,
            'description': "Single Transferable Vote with %u seats" % i,
            'category': 'stv',
            'validate_func': validateSTV,
            'vote_func': None,
            'tally_func': tallySTV
        },
    )
