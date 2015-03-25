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
import hashlib, json, random, os, sys, time
from __main__ import homedir, config

# SMTP Lib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTPException



def get(election, basedata, uid):
    if config.get("database", "dbsys") == "file":
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
    uid = hashlib.sha224("%s%s%s%s" % (email, basedata['hash'], time.time(), random.randint(1,99999999))).hexdigest()
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    if config.get("database", "dbsys") == "file":
        elpath = os.path.join(homedir, "issues", election)
        with open(elpath + "/voters.json", "r") as f:
            voters = json.loads(f.read())
            f.close()
        voters[email] = xhash
        with open(elpath + "/voters.json", "w") as f:
            f.write(json.dumps(voters))
            f.close()
    return uid, xhash

def remove(election, basedata, email):
    if config.get("database", "dbsys") == "file":
        elpath = os.path.join(homedir, "issues", election)
        with open(elpath + "/voters.json", "r") as f:
            voters = json.loads(f.read())
            f.close()
        if email in voters:
            del voters[email]
        with open(elpath + "/voters.json", "w") as f:
            f.write(json.dumps(voters))
            f.close()

def hasVoted(election, issue, uid):
    issue = issue.strip(".json")
    if config.get("database", "dbsys") == "file":
        path = os.path.join(homedir, "issues", election, issue)
        votes = {}
        if os.path.isfile(path + ".json.votes"):
            with open(path + ".json.votes", "r") as f:
                votes = json.loads(f.read())
                f.close()
        return True if uid in votes else False
    return False

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
       