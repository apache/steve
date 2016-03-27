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
try:
    from __main__ import config
except:
    import ConfigParser as configparser
    config = configparser.RawConfigParser()
    config.read("%s/../../../steve.cfg" % (os.path.dirname(__file__)))

# SMTP Lib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTPException

from lib import constants, election

backend = constants.initBackend(config)

def get(election, basedata, uid):
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    return backend.voter_get_uid(election, xhash)
    
        
def add(election, basedata, PID):
    uid = hashlib.sha224("%s%s%s%s" % (PID, basedata['hash'], time.time(), random.randint(1,99999999))).hexdigest()
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    backend.voter_add(election, PID, xhash)
    return uid, xhash
    
def remove(election, basedata, UID):
    backend.voter_remove(election, UID)
    

def hasVoted(election, issue, uid):
    issue = issue.strip(".json")
    return backend.voter_has_voted(election, issue, uid)

def ballots():
    try:
        from lib import gateway
        uid = gateway.uid()
        return backend.voter_ballots(uid) if uid else {}
    except:
        return {}

def regenerate(election, basedata, xhash):
    try:
        from lib import gateway
        uid = gateway.uid()
        backend.ballot_scrub(election, xhash)
        ballot, xhash = add(election, basedata, uid)
        return {
            'election': election,
            'ballot': ballot
        }
    except:
        return {'error': "No suitable gateway mechanism found"}
    
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
       