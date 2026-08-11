# Helpful SQL Statements

There are a few times when you may want to interact directly with the database
(typically `steve.db`) to perform bulk operations. Below are a few helpful
statements.

## Voter Management

Add a Person as a voter on all issues in the database (eg. for dev/testing):
```SQL
INSERT OR IGNORE INTO mayvote (pid, iid)
SELECT "alice", iid FROM issue
```
