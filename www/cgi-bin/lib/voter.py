import hashlib, json, random, os, sys
from __main__ import homedir, config

# SMTP Lib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart




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

def hasVoted(election, issue, uid):
    issue = issue.strip(".json")
    path = os.path.join(homedir, "issues", election, issue)
    votes = {}
    if os.path.isfile(path + ".json.votes"):
        with open(path + ".json.votes", "r") as f:
            votes = json.loads(f.read())
            f.close()
    return True if uid in votes else False

def email(rcpt, subject, message):
    sender = config.get("email", "sender")
    signature = config.get("email", "signature")
    receivers = [rcpt]
    msg = """From: %s
To: %s
Subject: %s

%s

With regards,
%s
--
Powered by Apache STeVe - https://steve.apache.org
""" % (sender, rcpt, subject, message, signature)
    
    try:
       smtpObj = smtplib.SMTP(config.get("email", "mta"))
       smtpObj.sendmail(sender, receivers, msg)         
    except SMTPException:
       raise Exception("Could not send email - SMTP server down?")
       