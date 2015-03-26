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
""" Simple YNA voting plugin """
from lib import constants

def tallyYNA(votes, issue):
    """ Simple YNA tallying
    :param votes: The JSON object from $issueid.json.votes
    :return: y,n,a as numbers
    """
    y = n = a = 0
    for vote in votes.values():
        if vote == 'y':
            y += 1
        elif vote == 'n':
            n += 1
        elif vote == 'a':
            a += 1
        else:
            raise Exception("Invalid vote found!")

    return {
        'votes': len(votes),
        'yes': y,
        'no': n,
        'abstain': a
    }

def validateYNA(vote, issue):
    "Tries to validate a vote, returns why if not valid, None otherwise"
    letters = ['y','n','a']
    if len(vote) != 1 or not vote in letters:
        return "Invalid vote. Accepted votes are: %s" % ", ".join(letters)
    return None

constants.appendVote (
    {
        'key': "yna",
        'description': "YNA (Yes/No/Abstain) vote",
        'category': 'yna',
        'validate_func': validateYNA,
        'vote_func': None,
        'tally_func': tallyYNA
    },
)