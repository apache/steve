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
# ----
#
# ### TBD: DOCCO
#

import pathlib

import asfpy.db

THIS_DIR = pathlib.Path(__file__).resolve().parent
QUERIES = THIS_DIR.parent / 'queries.yaml'


class PersonDB:

    def __init__(self, db_fname):
        self.db = asfpy.db.DB(db_fname,
                              yaml_fname=QUERIES, yaml_section='person')

    def __getattr__(self, name):
        "Proxy the cursors."
        return self.__dict__.get(name, getattr(self.db, name))

    def get_person(self, pid):
        "Return NAME, EMAIL for Person identified by PID."

        # NEVER return person.salt
        person = self.q_get_person.first_row(pid)
        if not person:
            raise PersonNotFound(pid)

        return person.name, person.email

    def add_person(self, pid, name, email):
        "Add or update a Person designated by PID."

        # If we ADD, then SALT will be NULL. If we UPDATE, then it will not
        # be touched (it should be NULL).
        self.c_add_person.perform(pid, name, email)

    def delete_person(self, pid):
        "Delete the Person designated by PID."

        # NOTE: if this person has ever been involved in a vote
        #   (ie. the PID exists in a "mayvote" row), then this will
        #   throw a referential integrity error.
        #
        ### maybe we just don't delete a person, ever?

        self.c_delete_person.perform(pid)

        # If the Person didn't exist, we deleted nothing.
        if self.c_delete_person.rowcount == 0:
            raise PersonNotFound(pid)
        # else .rowcount == 1

    def list_persons(self):
        "Return ordered EasyDict<PID, NAME, EMAIL> for each Person."

        ### switch to explicitly returning a generator?

        # Run the query to completion, and return the entire list of Persons.
        self.q_person.perform()
        return list(self.q_person.fetchall())  # asfpy.db.DB uses EasyDict


class PersonNotFound(Exception):
    def __init__(self, pid):
        self.pid = pid
        super().__init__(str(self))

    def __str__(self):
        return f'Person[P:{self.pid}] not found'
