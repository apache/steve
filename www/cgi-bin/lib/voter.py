import hashlib, json, random, os, sys
from __main__ import homedir

def get(election, basedata, uid):
    elpath = os.path.join(homedir, "issues", election)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
        xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
        for voter in voters:
            if voters[voter] == xhash:
                return voter
    return None
        
def add(election, basedata, email):
    uid = hashlib.sha512(email + basedata['hash'] + time.time() + random.randint(1,99999999)).hexdigest()
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    elpath = os.path.join(homedir, "issues", election)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
    with open(elpath + "/voters.json", "w") as f:
        f.write(json.dumps(voters))
        f.close()
    return uid, xhash

def remove(election, basedata, email):
    uid = hashlib.sha512(email + basedata['hash'] + time.time() + random.randint(1,99999999)).hexdigest()
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    elpath = os.path.join(homedir, "issues", election)
    with open(elpath + "/voters.json", "r") as f:
        voters = json.loads(f.read())
        f.close()
    if email in voters:
        del voters[email]
    with open(elpath + "/voters.json", "w") as f:
        f.write(json.dumps(voters))
        f.close()
    return uid, xhash

