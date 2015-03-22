import hashlib, json, random, os, sys, time
from __main__ import homedir, config
from os import listdir


def exists(election):
    elpath = os.path.join(homedir, "issues", election)
    return os.path.isdir(elpath)

def getBasedata(election, hideHash = False):
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        with open(elpath + "/basedata.json", "r") as f:
            data = f.read()
            f.close()
            basedata = json.loads(data)
            if hideHash and 'hash' in basedata:
                del basedata['hash']
            basedata['id'] = election
            return basedata
    return None
    
def getIssue(electionID, issueID):
    issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
    issuedata = None
    if os.path.isfile(issuepath):
        with open(issuepath, "r") as f:
            data = f.read()
            f.close()
            issuedata = json.loads(data)
        issuedata['id'] = issueID
        issuedata['APIURL'] = "https://%s/steve/voter/view/%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
        issuedata['prettyURL'] = "https://%s/steve/ballot?%s/%s" % (config.get("general", "rooturl"), electionID, issueID)
    return issuedata
    
def listIssues(election):
    issues = []
    elpath = os.path.join(homedir, "issues", election)
    if os.path.isdir(elpath):
        issues = [ f.strip(".json") for f in os.listdir(elpath) if os.path.isfile(os.path.join(elpath,f)) and f != "basedata.json" and f != "voters.json" and f.endswith(".json")]
    return issues

def vote(electionID, issueID, voterID, vote):
    votes = {}
    basedata = getBasedata(electionID)
    if basedata:
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath + ".votes"):
            with open(issuepath + ".votes", "r") as f:
                votes = json.loads(f.read())
                f.close()
        votes[voterID] = vote
        with open(issuepath + ".votes", "w") as f:
            f.write(json.dumps(votes))
            f.close()
        votehash = hashlib.sha224(basedata['hash'] + issueID + voterID + vote).hexdigest()
        return votehash
    else:
        raise Exception("No such election")


def invalidate(issueData, vote):
    letters = ['y','n','a']
    if issueData['type'].find("stv") == 0:
        letters = [chr(i) for i in range(ord('a'),ord('a') + len(issueData['candidates']))]
    for char in letters:
        if vote.count(char) > 1:
            return "Duplicate letters found"
    for char in vote:
        if not char in letters:
            return "Invalid characters in vote. Accepted are: %s" % ", ".join(letters)
    return None

def deleteIssue(electionID, issueID):
    if exists(electionID):
        issuepath = os.path.join(homedir, "issues", electionID, issueID) + ".json"
        if os.path.isfile(issuepath):
            os.unlink(issuepath)
        if os.path.isfile(issuepath + ".votes"):
            os.unlink(issuepath + ".votes")
        return True
    else:
        raise Exception("No such election")