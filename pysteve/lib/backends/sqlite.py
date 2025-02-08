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
import hashlib
import json
import time
from lib import constants
import asfpy.sqlite

"""SQLite database wrapper for STeVe v2 (PySTeVe)"""

DB_CREATE_STATEMENTS = (
    """
CREATE TABLE "elections" (
    "id"	TEXT PRIMARY KEY UNIQUE,
    "title"	TEXT NOT NULL,
    "owner"	TEXT NOT NULL,
    "monitors"	TEXT NOT NULL,
    "starts"	INTEGER,
    "ends"	INTEGER,
    "hash"	TEXT NOT NULL,
    "open"	TEXT NOT NULL,
    "closed" INTEGER
);""",
    """
CREATE TABLE "issues" (
    "id"	TEXT PRIMARY KEY UNIQUE,
    "election" TEXT NOT NULL,
    "title"	TEXT NOT NULL,
    "description"	TEXT NOT NULL,
    "type"	TEXT NOT NULL,
    "candidates"	TEXT,
    "seconds"	TEXT,
    "nominatedby"	TEXT
);""",
    """
CREATE TABLE "votes" (
    "eid"	TEXT PRIMARY KEY UNIQUE,
    "issue" TEXT NOT NULL,
    "election" TEXT NOT NULL,
    "key"	TEXT NOT NULL,
    "data"	TEXT NOT NULL
);""",
    """
CREATE TABLE "voters" (
    "id"	TEXT PRIMARY KEY UNIQUE,
    "election" TEXT NOT NULL,
    "hash"	TEXT NOT NULL,
    "uid"	TEXT NOT NULL
);""",
    """
CREATE TABLE "vote_history" (
    "id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
    "eid"   TEXT NOT NULL,
    "issue" TEXT NOT NULL,
    "election" TEXT NOT NULL,
    "key"	TEXT NOT NULL,
    "data"	TEXT NOT NULL
);
""",
)


class SteveSQLite(object):
    def __init__(self, config):
        self.config = config
        self.dbname = config.get("sqlite", "database")
        self.db = asfpy.sqlite.DB(self.dbname)
        if not self.db.table_exists("elections"):
            for stmt in DB_CREATE_STATEMENTS:
                self.db.runc(stmt)


def pickle(doc: dict):
    ndoc = {}
    for k, v in doc.items():
        if isinstance(v, list) or isinstance(v, dict) or (isinstance(v, str) and v.startswith("%JSON%:")):
            v = "%JSON%:" + json.dumps(v)
        ndoc[k] = v
    return ndoc


def unpickle(doc: dict):
    ndoc = {}
    for k, v in doc.items():
        if isinstance(v, str) and v.startswith("%JSON%:"):
            try:
                v = json.loads(v[7:])
            except json.JSONDecodeError:
                pass
        ndoc[k] = v
    return ndoc


class SQLiteBackend:

    def __init__(self, config):
        "Init - get config and turn it into an ES instance"
        self.DB = SteveSQLite(config)

    def document_exists(self, election, *issue):
        "Does this election or issue exist?"
        eid = election
        if issue and issue[0]:
            return self.DB.db.fetchone("issues", election=election, id=issue[0])
        return self.DB.db.fetchone("elections", id=eid)

    def get_basedata(self, election):
        "Get base data from an election"
        res = self.DB.db.fetchone("elections", id=election)
        if res:
            return unpickle(res)

    def close(self, election, reopen=False):
        "Mark an election as closed"
        basedata = self.get_basedata(election)
        if reopen == True:
            basedata["closed"] = 0
        else:
            basedata["closed"] = 1
        self.DB.db.update("elections", pickle(basedata), id=election)

    def issue_get(self, electionID, issueID):
        "Get JSON data from an issue"
        issuedata = None
        ihash = ""
        res = self.DB.db.fetchone("issues", id=issueID, election=electionID)
        if res:
            issuedata = unpickle(res)
            ihash = constants.hexdigest(json.dumps(issuedata))
        return issuedata, ihash

    def votes_get(self, electionID, issueID):
        "Read votes and return as a dict"
        res = [unpickle(x) for x in self.DB.db.fetch("votes", limit=None, election=electionID, issue=issueID)]
        if res:
            votes = {}
            for entry in res:
                votes[entry["key"]] = entry["data"]["vote"]
            return votes
        return {}

    def votes_get_raw(self, electionID, issueID):
        "Read votes and return raw format"
        res = [unpickle(x) for x in self.DB.db.fetch("votes", limit=None, election=electionID, issue=issueID)]
        if res:
            votes = []
            for entry in res:
                votes.append(entry)
            return votes
        return {}

    def vote_history(self, electionID, issueID):
        "Read vote history and return raw format"
        res = [unpickle(x) for x in self.DB.db.fetch("vote_history", limit=None, election=electionID, issue=issueID)]
        if res:
            votes = []
            for entry in res:
                votes.append(entry)
            return votes
        return []

    def election_create(self, _electionid, basedata):
        """Create a new election"""

        self.DB.db.insert("elections", pickle(basedata))

    def election_update(self, electionID, basedata):
        "Update an election with new data"
        self.DB.db.update("elections", pickle(basedata), id=electionID)

    def issue_update(self, electionID, issueID, issueData):
        "Update an issue with new data"
        # Make a clean issue document that only has the sqlite-defined fields in it
        issue_fields = ("id", "election", "title", "description", "type", "candidates", "seconds", "nominatedby")
        new_data = {k:v for k,v in issueData.items() if k in issue_fields}
        self.DB.db.update("issues", issueData, id=issueID, election=electionID)

    def issue_list(self, election):
        "List all issues in an election"
        issues = [x["id"] for x in self.DB.db.fetch("issues", limit=None, election=election)]
        return issues

    def election_list(self):
        "List all elections"
        elections = [x['id'] for x in self.DB.db.fetch("elections", limit=None)]
        return elections

    def vote(self, electionID, issueID, uid, vote, vhash=None):
        "Casts a vote on an issue"
        eid = constants.hexdigest(electionID + ":" + issueID + ":" + uid)
        now = time.time()
        if vhash:
            eid = vhash
        doc = pickle(
            {"eid": eid, "issue": issueID, "election": electionID, "key": uid, "data": {"timestamp": now, "vote": vote}}
        )
        self.DB.db.upsert("votes", doc, eid=eid)
        self.DB.db.insert("vote_history", doc)

    def issue_delete(self, electionID, issueID):
        "Deletes an issue if it exists"
        self.DB.db.delete("issues", election=electionID, id=issueID)

    def issue_create(self, electionID, issueID, data):
        "Create an issue"
        # iid = hashlib.sha224((electionID + "/" + issueID).encode("utf-8")).hexdigest()
        self.DB.db.insert("issues", pickle(data))

    def voter_get_uid(self, electionID, votekey):
        "Get the UID/email for a voter given the vote key hash"
        # First, try the raw hash as an ID

        res = self.DB.db.fetchone("voters", id=votekey)
        if res:
            return unpickle(res)['uid']

        # Try looking for hash key
        res = self.DB.db.fetchone("voters", hash=votekey)
        if res:
            return unpickle(res)['uid']

        return False  # No ballot found.

    def voter_add(self, election, PID, xhash):
        "Add a voter to the DB"
        eid = constants.hexdigest(election + ":" + PID)
        doc = pickle({"id": eid, "election": election, "hash": xhash, "uid": PID})
        self.DB.db.upsert("voters", doc, id=eid)

    def ballot_scrub(self, election, xhash, uid=None):
        "Scrub a ballot"
        if uid:
            xhash = constants.hexdigest(election + ":" + uid)

        # Find ballots and votes matching
        bid = self.voter_get_uid(election, xhash)
        if not bid:
            return None
        issues = self.issue_list(election)
        for issue in issues:
            vhash = constants.hexdigest(xhash + issue)
            try:
                self.DB.db.delete("votes", eid=vhash)
            except:
                pass
        return True

    def voter_remove(self, election, UID):
        "Remove the voter with the given UID"
        votehash = constants.hexdigest(election + ":" + UID)
        self.DB.db.delete("voters", id=votehash)

    def voter_has_voted(self, election, issue, uid):
        "Return true if the voter has voted on this issue, otherwise false"
        eid = constants.hexdigest(election + ":" + issue + ":" + uid)
        try:
            return self.DB.db.fetchone(doc_type="votes", id=eid)
        except:
            return False

    def voter_ballots(self, UID):
        """Find all elections (and ballots) this user has participated in"""

        # First, get all elections
        elections = {}

        res = [unpickle(x) for x in self.DB.db.fetch("elections", limit=None)]
        for election in res:
            # Mark election open or closed
            elections[election["id"]] = {"title": election["title"], "open": False if election["closed"] else True}

        # Then, get all ballots and note whether they still apply or not
        ballots = {}
        res = [pickle(x) for x in self.DB.db.fetch("voters", limit=100, uid=UID)]
        for ballot in res:
            ballots[ballot["election"]] = {"ballot": ballot["id"], "metadata": elections[ballot["election"]]}
        return ballots


constants.appendBackend("sqlite", SQLiteBackend)
