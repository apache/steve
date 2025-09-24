/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/* There is a per-install SQLite database containing all election data
   for the site. This file defines/constructs the schema of that database.

   Note that foreign key references are defined within this scheme. For
   these to be enforced at runtime, you must use a PRAGMA statement:
       conn.execute('PRAGMA foreign_keys = ON')
   */

/* ### $ sqlite3 steve.db < steve/v3/schema.sql
   ###
   ### OR:
   ### >>> import sqlite3
   ### >>> conn = sqlite3.connect('steve.db')
   ### >>> conn.executescript(open('schema.sql').read())
   ###
   ### ? maybe: conn.commit() and/or conn.close() ... the DML statements
   ### don't seem to require full closure of connection.
   */


/* --------------------------------------------------------------------- */

/* Various Election metadata.

   An Election has three states:

     1. Editable. The election is being set up. Issues and Persons of
        record can be added, edited, and deleted. The Election's title
        may be changed (EID is fixed, however).
        DEFINITION: salt and opened_key are NULL. closed is n/a.

     2. Open. The election is now open for voting.
        DEFINITION: salt and opened_key are NOT NULL. closed is NULL or 0.

     3. Closed. The election is closed.
        DEFINITION: salt and opened_key are NOT NULL. closed is 1.
*/
CREATE TABLE elections (

    /* The Election ID; 10 hex characters. We do not use AUTOINCREMENT,
       so that URLs for Elections cannot be deduced.  */
    eid  TEXT
           PRIMARY KEY NOT NULL
           CHECK (length(eid) = 10
                  AND eid GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),

    /* Title of this election.  */
    title  TEXT NOT NULL,

    /* Who is the owner/creator of this election?
       Note: no need to CHECK OWNER_PID as it refers to a foreign table
       where its propriety is enforced.  */
    owner_pid  TEXT NOT NULL,

    /* What authz group is allowed to edit this election? If NULL,
       then only the OWNER_PID can edit.  */
    /* ### contents/format is TBD; think "which PMC" or "Foundation"  */
    authz  TEXT,

    /* ### if we have monitors, they go here.  */
    /* ### skip monitors. only OWNER_PID may monitor.  */

    /* A salt value to use for hashing this Election. 16 bytes.
       This will be NULL until the Election is opened.  */
    salt  BLOB  CHECK (salt IS NULL OR length(salt) = 16),

    /* If this Election has been opened for voting, then we store
       the OpenedKey here to avoid recomputing. 32 bytes.
       This will be NULL until the Election is opened.  */
    opened_key  BLOB  CHECK (opened_key IS NULL OR length(opened_key) = 32),

    /* Has this election been closed? NULL or 0 for not-closed (see
       SALT and OPENED_KEY to determine if the election has been
       opened). 1 for closed (implies it was opened).  */
    closed  INTEGER  CHECK (closed IS NULL OR closed IN (0, 1)),


    /* Enforce/declare/document relationships.  */
    FOREIGN KEY (owner_pid) REFERENCES person(pid)
    ON DELETE RESTRICT
    ON UPDATE NO ACTION

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The set of Issues to vote upon for a given Election.  */
CREATE TABLE issues (

    /* The Issue ID; 10 hex characters. We do not use AUTOINCREMENT,
       so that URLs for Issues cannot be deduced.  */
    iid  TEXT
           PRIMARY KEY NOT NULL
           CHECK (length(iid) = 10
                  AND iid GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),

    /* Which election is this issue associated with?
       Note: no need to CHECK EID as it refers to a foreign table where
       its propriety is enforced.  */
    eid  TEXT NOT NULL,

    /* Simple one-line title for this issue.  */
    title  TEXT NOT NULL,

    /* An optional, longer description of the issue.  */
    description  TEXT,

    /* The type of this issue's vote mechanism (eg. yna, stv, ...). This
       is one of an enumerated set of values.
       ### see <here> for the enumeration.  */
    type  TEXT NOT NULL,

    /* Per-type set of key/value pairs specifying additional data. This
       value is JSON-formatted  */
    kv  TEXT,

    /* Enforce/declare/document relationships.  */
    FOREIGN KEY (eid) REFERENCES elections(eid)
    ON DELETE RESTRICT
    ON UPDATE NO ACTION

    ) STRICT;

CREATE INDEX idx_issues_eid ON issues(eid);

/* --------------------------------------------------------------------- */

/* The set of Persons ever seen, across all Elections.  */
CREATE TABLE person (

    /* An id assigned to the person (eg. an LDAP username).  */
    pid  TEXT PRIMARY KEY NOT NULL,

    /* Optional human-readable name for this person.  */
    name  TEXT,

    /* How to contact this person (eg. to send a ballot link).  */
    email  TEXT NOT NULL

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The set of Persons who may vote on an Issue (aka eligible/allowed).  */
CREATE TABLE mayvote (

    /* The Person who may vote...  */
    pid  TEXT NOT NULL,

    /* ... on this Issue.  */
    iid  TEXT NOT NULL,

    /* A salt value for hashing this Person/Issue pair into a vote_token.
       Also used via key-stretching to create an encryption key for the
       vote values. This will be NULL until the Election (containing IID)
       is opened.  16 bytes.  */
    salt  BLOB  CHECK (salt IS NULL OR length(salt) = 16),

    /* The pair should be unique.  */
    PRIMARY KEY (pid, iid),

    /* Note: no need to check PID/IID columns as they refer to a foreign
       table where their propriety is enforced.  */

    /* Enforce/declare/document relationships.  */
    FOREIGN KEY (pid) REFERENCES person(pid)
    ON DELETE RESTRICT
    ON UPDATE NO ACTION,

    FOREIGN KEY (iid) REFERENCES issues(iid)
    ON DELETE RESTRICT
    ON UPDATE NO ACTION

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The registered votes, once the Election has been opened. Note that
   duplicates of (person, issue) may occur (the vote_token will be the
   same), as re-voting is allowed. Only the latest is used.  */
CREATE TABLE votes (

    /* The key is auto-incrementing to provide a record of insert-order,
       so that we have an ordering to find the "most recent" when
       re-voting on an issue.
       Note: an integer primary key is an alias for _ROWID_.  */
    vid  INTEGER PRIMARY KEY AUTOINCREMENT,

    /* A hashed-based token (32 bytes) based on a (Person, Issue) pair
       from the MAYVOTE table. Used to produce a key for encryption.   */
    vote_token  BLOB NOT NULL  CHECK (length(vote_token) = 32),

    /* An encrypted form of the vote.  */
    ciphertext  BLOB NOT NULL

    ) STRICT;

/* ### review queries.yaml to figure out proper indexes  */
CREATE INDEX idx_by_vote_token ON votes (vote_token);

/* --------------------------------------------------------------------- */
