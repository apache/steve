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
# Convenience wrapper for working with a SQLite database.
#
# This wrapper has several primary purposes:
#
#   1. Easily create a cursor for each statement that might be
#      executed by the application.
#   2. Remember the specific string object for those statements,
#      and re-use them in cursor.execute() for better performance.
#   3. Rows fetched with SELECT statements are wrapped into a
#      namedtuple() instance, such that columns can be easily
#      accessed as attributes or numerically indexed as a tuple, 
#

import sqlite3
import collections
import functools


class DB:

    def __init__(self, fname):

        def row_factory(cursor, row):
            "Possibly apply namedtuple() to the returned row."
            return self.factories.get(cursor, lambda *row: row)(*row)

        # Note: isolation_level=None means autocommit mode.
        self.conn = sqlite3.connect(fname, isolation_level=None)
        self.conn.row_factory = row_factory

        # CURSOR : FACTORY
        self.factories = { }

    def _cursor_for(self, statement):
        return self.conn.cursor(functools.partial(NamedTupleCursor,
                                                  statement))

    def add_query(self, table, query):
        "Return a cursor to use for this QUERY against TABLE."

        # The query must select all columns.
        assert query[:9].lower() == 'select * '

        # Get all column names for TABLE.
        cur = self.conn.execute(f'select * from {table} limit 1')
        names = [ info[0] for info in cur.description ]

        # We don't need the results, but cannot leave the cursor hanging,
        # as it establishes a lock on this table. This likely closes as
        # this method exits, but let's not rely upon that.
        cur.close()

        # Create a factory for turning rows into namedtuples.
        factory = collections.namedtuple(f'row_factory_{len(self.factories)}',
                                         names, rename=True,
                                         module=DB.__module__)

        # Register the row-wrapper factory for this cursor.
        cursor = self._cursor_for(query)
        self.factories[cursor] = factory
        return cursor

    def add_statement(self, statement):
        "Return a cursor for use with a DML SQL statement."

        # Note: rows should not be returned for this statement, and
        # (thus) the row_factory should not be called. If called, the
        # original row will be returned.
        return self._cursor_for(statement)


class NamedTupleCursor(sqlite3.Cursor):

    def __init__(self, statement, *args, **kw):
        super().__init__(*args, **kw)
        self.statement = statement

    def perform(self, params=()):
        "Perform the statement with PARAMs, or prepare the query."

        # Use the exact same STATEMENT each time. Python's SQLite module
        # caches the parsed statement, if the string is the same object.
        self.execute(self.statement, params)

    def first_row(self, params=()):
        "Helper method to fetch the first row of a query."
        self.perform(params)
        row = self.fetchone()
        _ = self.fetchall()  # run the cursor to completion; should be empty
        return row
