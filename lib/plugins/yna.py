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
        if vote == 'n':
            n += 1
        if vote == 'a':
            a += 1

    return {
        'votes': len(votes),
        'yes': y,
        'no': n,
        'abstain': a
    }

def validateYNA(vote, issue):
    "Tries to invalidate a vote, returns why if succeeded, None otherwise"
    letters = ['y','n','a']
    for char in letters:
        if vote.count(char) > 1:
            return "Duplicate letters found"
    for char in vote:
        if char not in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None

constants.VOTE_TYPES += (
    {
        'key': "yna",
        'description': "YNA (Yes/No/Abstain) vote",
        'category': 'yna',
        'validate_func': validateYNA,
        'vote_func': None,
        'tally_func': tallyYNA
    },
)