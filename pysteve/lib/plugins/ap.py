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
""" ASF PMC style voting plugin """
from lib import constants

def tallyAP(votes, issue):
    """ Simple YNA tallying
    :param votes: The JSON object from $issueid.json.votes
    :return: dict with y,n,a,by,bn numbers as well as pretty-printed version
    """
    y = n = a = 0
    by = bn = 0
    # For each vote cast, tally it
    for vote in votes.values():
        if vote == 'y':
            y += 1
        elif vote == 'n':
            n += 1
        elif vote == 'a':
            a += 1
        elif vote == 'by':
            by += 1
        elif vote == 'bn':
            bn += 1
        else:
            raise Exception("Invalid vote found in votes db!")

    js = {
        'votes': len(votes),
        'yes': y,
        'no': n,
        'abstain': a,
        'binding_yes': by,
        'binding_no': bn
    }
    
    return js, """
Yes:            %4u
No:             %4u
Abstain:        %4u
Binding Yes:    %4u
Binding No:     %4u
""" % (y,n,a,by,bn)


def validateAP(vote, issue):
    "Tries to validate a vote, returns why if not valid, None otherwise"
    letters = ['y','n','a', 'by', 'bn']
    if len(vote) >= 3 or not vote in letters:
        return "Invalid vote. Accepted votes are: %s" % ", ".join(letters)
    return None


# Verification process
def verifyAP(basedata, issueID, voterID, vote, uid):
    "Invalidate a binding vote if not allowed to cast such"
    if vote.startswith('b'):
        # Simple check example: if not apache committer, discard vote if binding
        if not uid.endswith("@apache.org"):
            raise Exception("You are not allowed to cast a binding vote!")


constants.appendVote(
    {
        'key': "ap",
        'description': "PMC Style vote (YNA with binding votes)",
        'category': 'ap',
        'validate_func': validateAP,
        'vote_func': verifyAP,
        'tally_func': tallyAP
    },
)