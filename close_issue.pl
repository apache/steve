From: Roy T. Fielding <fielding@apache.org>
To: brian@apache.org, jim@apache.org
Subject: ssh-based voter

Hi guys,

I would like to create an ssh-based voter tool.  The general design
is as follows:

  o  A "voter" user and group are created on cvs.apache.org with a
     home directory and no password;

  o  sudo access to voter is given to members of group voter, initially
     fielding and jim;

/home/voter/bin/make_issue

  o  setuid voter

  o  a program for creating issues to be voted upon;

  o  creates an issue number, a directory (/home/voter/issue/nnnnnn/),
     and fills it with files for the allowed voters, election monitors,
     the tally file, and other things;

  o  mails to each voter their hash-id to be used, issue number, and
     some text explaining the issue;

  o  creates a table of hash of "nnnnnn:hash-id" for use in validating
     votes, verifying that the values are unique.

/home/voter/bin/vote

  o  setuid voter

  o  a simple program that takes as arguments a voter-hash, issue
     number, and vote (yes/no/abstain or a multi-selection word);

  o  validates arguments based on type of issue;

  o  appends timestamp, hashed-hash-id, and vote to the tally;

  o  sends mail to voter indicating that their vote has been received
     (but not the contents of the vote);

  o  sends mail to the election monitor(s) indicating the vote that
     was received and the hashed-hash-id (to identify repeats).

/home/voter/bin/close_issue

  o  setuid voter

  o  sets a marker indicating no more votes accepted for issue;

  o  reads in tally, counting only last recorded vote per hashed-hash-id;

  o  mails summary to election monitor(s)

  o  [maybe] creates an HTML summary of results as
        /home/voter/public_html/issue_nnnnnn.html

I think that's it.  Did I miss something?

I do not claim that this is the perfect voting solution.  Some of the
problems:

  -  it allows the sudo users and root users the ability to modify
     the votes after they have been received, though this should be
     detected unless they also spoof or intercept mail to the monitors.

  -  it allows several ways for an observer to connect-the-dots
     between the voting persons and their hash-id, and thus to their
     vote, particularly if the observer has access to the mail queue.

  -  it allows the sudo users and root users the ability to modify
     the vote or close_issue commands, changing the results.

However, these drawbacks are not significantly worse than a
traditional ballot box and manual counting at a meeting, at least
when we compare it to the stockholder votes by proxy that are
commonly done for public companies.  I think this will be sufficient
to keep votes accurate and anonymous given a trusting environment.

I can write the scripts, but I'll need root to create the user and
sudo stuff.  And then I'll test it on some dummy issues before we
use it for real.  Thoughts?

....Roy
