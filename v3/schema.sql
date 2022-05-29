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

/* ### TBD DOCCO.  */

/* ### $ sqlite3 testing.db < schema.sql  */


/* --------------------------------------------------------------------- */

/* Various metadata about the Election contained in this database.
   Only one row will exist.  */
CREATE TABLE METADATA (

    /* The Election ID. This value might be replicated in the
       filesystem holding this database. To remain independent of
       application file choices, the ID is stored here.  */
    eid  TEXT PRIMARY KEY NOT NULL,

    /* Title of this election.  */
    title  TEXT NOT NULL,

    /* ### should we include a start/stop time?  */
    /* ### if we have monitors, they go here.  */
    /* ### maybe add an owner?  */

    /* A salt value to use for hashing this Election. 16 bytes.
       This will be NULL until the Election is opened.  */
    salt  BLOB,

    /* If this Election has been opened for voting, then we store
       the OpenedKey here to avoid recomputing. 32 bytes.
       This will be NULL until the Election is opened.  */
    opened_key  BLOB

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The set of issues to vote upon in this Election.  */
CREATE TABLE ISSUES (

    /* The Issue ID, matching [-a-zA-Z0-9]+  */
    iid  TEXT PRIMARY KEY NOT NULL,

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

    /* A salt value to use for hashing this Issue. 16 bytes.
       This will be NULL until the Election is opened.  */
    salt  BLOB

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The set of people "on record" for this Election. Only these people
   may vote.  */
CREATE TABLE RECORD (

    /* An id assigned to the user (eg. an LDAP username).  */
    rid  TEXT PRIMARY KEY NOT NULL,

    /* Optional human-readable name for this user.  */
    name  TEXT,

    /* How to contact this person (ie. to send a ballot link).  */
    email  TEXT NOT NULL,

    /* A salt value to use for hashing this Participant. 16 bytes.
       This will be NULL until the Election is opened.  */
    salt  BLOB

    ) STRICT;

/* --------------------------------------------------------------------- */

/* The registered votes, once the Election has been opened. Note that
   duplicates of (voter, issue) may occur, as re-voting is allowed. Only
   the latest is used.  */
CREATE TABLE VOTES (

    /* The key is auto-incrementing to provide a record of insert-order,
       so that we have an ordering to find the "most recent" when
       re-voting on an issue.
       Note: an integer primary key is an alias for _ROWID_.  */
    vid  INTEGER PRIMARY KEY AUTOINCREMENT,

    /* A hashed token representing a single Participant.  32 bytes.  */
    voter_token  BLOB NOT NULL,

    /* A hashed token representing an issue.  32 bytes.  */
    issue_token  BLOB NOT NULL,

    /* A binary value used to salt the token's encryption.  16 bytes.  */
    salt  BLOB NOT NULL,

    /* An encrypted form of the vote.  */
    token  TEXT NOT NULL

    ) STRICT;

CREATE INDEX I_BY_VOTER ON VOTES (voter_token);
CREATE INDEX I_BY_ISSUE ON VOTES (issue_token);

/* --------------------------------------------------------------------- */
