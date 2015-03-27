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

es = None

if config.get("database", "dbsys") == "elasticsearch":
    from elasticsearch import Elasticsearch
    es = Elasticsearch([
                    {
                        'host': config.get("elasticsearch", "host"),
                        'port': int(config.get("elasticsearch", "port")),
                        'url_prefix': config.get("elasticsearch", "uri"),
                        'use_ssl': False if config.get("elasticsearch", "secure") == "false" else True
                    },
                ])
    if not es.indices.exists("steve"):
        es.indices.create(index = "steve", body = {
                "settings": {
                    "number_of_shards" : 3,
                    "number_of_replicas" : 1
                }
            }
        )
    


def get(election, basedata, uid):
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        elpath = os.path.join(homedir, "issues", election)
        with open(elpath + "/voters.json", "r") as f:
            voters = json.loads(f.read())
            f.close()
            for voter in voters:
                if voters[voter] == xhash:
                    return voter
    elif dbtype == "elasticsearch":
        try:
            res = es.search(index="steve", doc_type="voters", q = "election:%s" % election, size = 999999)
            results = len(res['hits']['hits'])
            if results > 0:
                for entry in res['hits']['hits']:
                    voter = entry['_source']
                    if voter['hash'] == xhash:
                        return voter['uid']
        except:
            return False # ES Error, probably not seeded the voters doc yet
    return None
        
def add(election, basedata, PID):
    uid = hashlib.sha224("%s%s%s%s" % (PID, basedata['hash'], time.time(), random.randint(1,99999999))).hexdigest()
    xhash = hashlib.sha512(basedata['hash'] + uid).hexdigest()
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        elpath = os.path.join(homedir, "issues", election)
        with open(elpath + "/voters.json", "r") as f:
            voters = json.loads(f.read())
            f.close()
        voters[PID] = xhash
        with open(elpath + "/voters.json", "w") as f:
            f.write(json.dumps(voters))
            f.close()
    elif dbtype == "elasticsearch":
        eid = hashlib.sha224(election + ":" + PID).hexdigest()
        es.index(index="steve", doc_type="voters", id=eid, body = {
            'election': election,
            'hash': xhash,
            'uid': PID
            }
        )
    return uid, xhash

def remove(election, basedata, UID):
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        elpath = os.path.join(homedir, "issues", election)
        with open(elpath + "/voters.json", "r") as f:
            voters = json.loads(f.read())
            f.close()
        if UID in voters:
            del voters[UID]
        with open(elpath + "/voters.json", "w") as f:
            f.write(json.dumps(voters))
            f.close()
    elif dbtype == "elasticsearch":
        eid = hashlib.sha224(election + ":" + UID).hexdigest()
        es.delete(index="steve", doc_type="voters", id=votehash);

def hasVoted(election, issue, uid):
    issue = issue.strip(".json")
    dbtype = config.get("database", "dbsys")
    if dbtype == "file":
        path = os.path.join(homedir, "issues", election, issue)
        votes = {}
        if os.path.isfile(path + ".json.votes"):
            with open(path + ".json.votes", "r") as f:
                votes = json.loads(f.read())
                f.close()
        return True if uid in votes else False
    elif dbtype == "elasticsearch":
        eid = hashlib.sha224(election + ":" + uid).hexdigest()
        try:
            res = es.search(index="steve", doc_type="voters", sort = "id", q = "_id:%s" % eid, size = 1)
            results = len(res['hits']['hits'])
            if results > 0:
                return True
        except:
            return False
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
       