#!/usr/bin/perl
#####
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#####
# make_issue
# A program for creating issues to be voted upon by the named "group"
#
# o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
# o  creates an issue directory (/home/voter/issues/group/YYYYMMDD-name/),
#    and fills it with files for the issue info, election monitors,
#    and tally file;
#
# o  creates tables of hash-ids and hashed-hash-ids for use in validating
#    votes, verifying that the values are unique;
#
# o  mails to the vote monitors an alert message to start tallying;
#
# o  mails to each voter their hash-id to be used, issue number, and
#    some text explaining the issue.
#
# Originally created by Roy Fielding
#
BEGIN {
    unshift @INC, "/home/voter/bin";
}
require "getopts.pl";
use randomize;
use ballots;
use steve;

umask(0077);
$| = 1;                                     # Make STDOUT unbuffered

$pname = $0;                                # executable name for errors
$pname =~ s#^.*/##;

# ==========================================================================
# ==========================================================================
# Print the usage information if help requested (-h) or a bad option given.
#
sub usage
{
    die <<"EndUsage";
usage: $pname [-h] [-b] [-g group] [-s start_date] [-i issue] [-f infofile]
                    [-m monitors] [-v vote_type )]
$pname -- Make an issue for managing an on-line, anonymous voting process
Options:
     -h  (help) -- just display this message and quit
     -b  (batch) -- batch processing: assume 'ok' unless errors
     -g  group  -- create an issue for an existing group of voters
     -s  date   -- YYYYMMDD format of date that voting is allowed to start
     -i  issue  -- append this alphanumeric string to start date as issue name
     -f  file   -- send the contents of this file to each voter as explanation
     -m  monitors -- e-mail address(es) for sending mail to vote monitor(s)
     -v  type   -- type of vote: yna = Yes/No/Abstain,
                   stvN = single transferable vote for [1-9] slots,
                   selectN = vote for [1-9] of the candidates

EndUsage
}

# ==========================================================================
# Get the command-line options or input from the user

undef $opt_h;
undef $opt_b;

if (!(&Getopts('hbg:s:i:f:m:v:')) || defined($opt_h)) { &usage; }

if (defined($opt_g)) {
    $group = $opt_g;
}
else {
    $group = &get_input_line("group name for voters on this issue", 1);
}
if ($group !~ /^\w+$/) {
    die "$pname: group name must be an alphanumeric token\n";
}

if (defined($opt_s)) {
    $start_date = $opt_s;
}
else {
    $start_date = &get_input_line("YYYYMMDD date that voting starts", 1);
}
if ($start_date !~ /^[2-9]\d\d\d(0[1-9]|1[012])([012]\d|3[01])$/) {
    die "$pname: start date must be formatted as YYYYMMDD, like 20020930\n";
}

if (defined($opt_i)) {
    $issue = $opt_i;
}
else {
    $issue = &get_input_line("short issue name to append to date", 1);
}
if ($issue !~ /^\w+$/) {
    die "$pname: issue name must be an alphanumeric token\n";
}

if (defined($opt_f)) {
    $infofile = $opt_f;
}
else {
    $infofile = &get_input_line("file pathname of issue info on $host", 1);
}
if (!(-e $infofile)) {
    die "$pname: info file does not exist: $infofile\n";
}
if ($infofile =~ /(\/etc\/|$issuedir)/) {
    die "$pname: forbidden to read info files in that directory\n";
}

if (defined($opt_m)) {
    $monitors = $opt_m;
}
else {
    $monitors = &get_input_line("e-mail address(es) for vote monitors", 1);
}
if ($monitors !~ /\@/) {
    die "$pname: vote monitor must be an Internet e-mail address\n";
}

if (defined($opt_v)) {
    $vote_type = $opt_v;
}
else {
    $vote_type = &get_input_line("vote type: yna, stvN, or selectN (N=1-9)", 1);
}
if ($vote_type =~ /^yna$/i) {
    $selector = 0;
    $style = "yes, no, or abstain";
}
elsif ($vote_type =~ /^stv([1-9])$/i) {
    $selector = $1;
    $style = "single transferable vote for $selector slots";
}
elsif ($vote_type =~ /^select([1-9])$/i) {
    $selector = $1;
    $style = "select $selector of the candidates labeled [a-z0-9]";
}
else {
    die "$pname: vote type must be yna, stvN, or selectN (N=[1-9])\n";
}

if (defined($opt_b)) {
    $batch = 1;
}
else {
    $batch = 0;
}

# ==========================================================================
# Check the voter group and read the list of voter addresses

die "$pname: cannot find $issuedir\n" unless (-d $issuedir);
$issuedir .= "/$group";
if (-d $issuedir) {
    die "$pname: you lack permissions on $issuedir\n"
        unless (-o _ && -r _ && -w _ && -x _);
}
else {
    die "$pname: group $group has not been created yet, see votegroup\n";
}

$votersfile = "$issuedir/voters";
@voters = &get_group($votersfile);
if ($#voters < 0) {
    die "$pname: $group must be an existing voter group: see votegroup\n";
}

# ==========================================================================
# Create directory for new issue only if it doesn't exist

$issuename = "$group-$start_date-$issue";
print "Creating new issue: $issuename\n";

$issuedir .= "/$start_date-$issue";
if (-e $issuedir) { die "$pname: $issuedir already exists\n"; }
mkdir($issuedir, 0700) || die "$pname: cannot mkdir $issuedir: $!\n";

# ==========================================================================
# Create issue information file (needs to be done before voter hash)

$issueaddr = 'voter@apache.org';

$issuefile = "$issuedir/issue";

open(ISF, ">$issuefile") || die "$pname: cannot open issue file: $!\n";
print ISF <<"EndOutput";
Hello Apache $group,

A call for votes has been declared for the following:

   Issue: $issuename
   Voting style: $style

EndOutput

open(INFILE, $infofile) || die "$pname: cannot open info file: $!\n";
print ISF <INFILE>;
close(INFILE);
close(ISF);

# ==========================================================================
# Create a table of voter hash-ids and verify uniqueness

for (;;) {
    $issid = &filestuff($issuefile);
    $monhash = &get_hash_of("$issid:$monitors");
    foreach $voter (@voters) {
        $h1 = &get_hash_of("$issid:$voter");
        $h2 = &get_hash_of("$issid:$h1");
        $hash1{$voter} = $h1;
        $hash2{$voter} = $h2;
        $invert1{$h1} = $voter;
        $invert2{$h2} = $voter;
    }
    $numh1 = scalar(keys(%hash1));
    $numh2 = scalar(keys(%hash2));
    $numi1 = scalar(keys(%invert1));
    $numi2 = scalar(keys(%invert2));
    last if (($numh1 == $numi1) && ($numh2 == $numi2));
    $h1 = &get_input_line("anything to retry collision-free hash", 1);
    system($TOUCH, $issuefile);
}
# &debug_hash;

# ==========================================================================
# Write list of monitors to issuedir/monitors
$monfile = "$issuedir/monitors";

open(MON, ">$monfile") || die "$pname: cannot open monitors file: $!\n";
print MON "$monitors\n";
close(MON);

# ==========================================================================
# Write type of vote to issuedir/vote_type
$typefile = "$issuedir/vote_type";

open(MON, ">$typefile") || die "$pname: cannot open vote type file: $!\n";
print MON "$vote_type\n";
if ($selector == 0) {
    @ballots = ( "yes\n", "no\n", "abstain\n");
} else {
    open(INFILE, $issuefile) || die "$pname: cannot open issue file: $!\n";
    @ballots = ballots(<INFILE>);
    close(INFILE);
}
print MON @ballots;
close(MON);

# ==========================================================================
# Verify with user that the info file is okay before mailing everyone.

print "Here is the issue information to be sent to each voter:\n";
print "==============================================================\n";
system($CAT, $issuefile);
&explain_vote(*STDOUT, 'unique-hash-key');
print "==============================================================\n";
do {
    $_ = ($batch ? "ok" : &get_input_line('"ok" to accept or "abort" to delete issue', 0));
    if (/^abort$/i) {
        system('rm', '-rf', $issuedir);
        exit(1);
    }
} until (/^ok/i);

# ==========================================================================
# Verify with user that the voters file is okay before mailing everyone.

print "Here is the list of voter e-mail addresses:\n";
print "==============================================================\n";
for $voter (@voters) {
    print $voter, "\n";
}
print "==============================================================\n";
do {
    $_ = ($batch ? "ok" : &get_input_line('"ok" to accept or "abort" to delete issue', 0));
    if (/^abort$/i) {
        system('rm', '-rf', $issuedir);
        exit(1);
    }
} until (/^ok/i);

# ==========================================================================
# Send mail to monitors telling them that the issue has been put to
# a vote, including the list of valid hashed hash-ids, sigs of files,
# and the issue info file.

open (MAIL, "|$SENDMAIL -t -f$issueaddr") || die("cannot send mail: $!\n");

print MAIL <<"EndOutput";
From: "Apache voting tool" <$issueaddr>
To: $monitors
Subject: Monitoring vote on $issuename

You have been selected as a vote monitor for Apache

   Issue: $issuename
   Voting style: $style

EndOutput
open(INFILE, $infofile) || die "$pname: cannot open info file: $!\n";
print MAIL <INFILE>;
close(INFILE);

print MAIL <<"EndOutput";

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

The voting system will record a tally of the votes as they are received
and will report that to you when the voting is closed.  To close voting,
use ssh to login to $host and then run

   /home/voter/bin/close_issue $issuename $monhash

For verification purposes, you will be receiving an e-mail notification
of each vote submitted by the voters.  Repeat votes should be considered
a complete replacement of the person's prior vote.  Your primary role in
all of this is to compare the votes you received with the results that
are tallied automatically, letting the group know if there is a
significant difference.  Any change made to the issue files during the
voting process will immediately invalidate the hash IDs and kill voting.

The following $numh2 voters are valid, as identified by the double-hashed ID
that will be sent to you when a vote is recorded.  Note that these IDs are
different from the single-hash IDs used by the voters when voting.

EndOutput

foreach $voter (sort(values(%hash2))) {
    print MAIL "   voter: $voter\n";
}

# Collect hash signatures of voter files that should not change
@vfiles = (
    "$votersfile",
    "$issuefile",
    "$monfile",
    "$typefile",
    "$homedir/bin/make_issue",
    "$homedir/bin/make_issue.pl",
    "$homedir/bin/vote",
    "$homedir/bin/vote.pl",
    "$homedir/bin/close_issue",
    "$homedir/bin/close_issue.pl"
);

print MAIL "\nThe following explains the voting process to voters:\n";
&explain_vote(*MAIL, 'unique-hash-key');
print MAIL "\nCurrent file digests:\n\n";
foreach $vf (@vfiles) {
    $pf = $vf;
    $pf =~ s/^$homedir\///o;
    print(MAIL &hash_file($vf), ': ', $pf, "\n");
}
close(MAIL);

# ==========================================================================
# Touch tally file to allow voting to begin
# -- Theoretically, this could be done by a another program with "at"
#    scheduling to prevent people from voting too early, but why bother?

system($TOUCH, "$issuedir/tally");

# ==========================================================================
# Send mail to voters telling them that the issue has been put to vote,
# including the info file and their commands.

while (($voter, $h1) = each %hash1) {
    print "Sending mail to voter: $voter\n";
########################################### for debugging
#   print "                hash1: $h1\n";
#   open (MAIL, ">>debug.txt") ||
########################################### replace next line
    open (MAIL, "|$SENDMAIL -t -f$issueaddr") ||
        die("cannot send mail to $voter: $!\n");

    print MAIL <<"EndOutput";
From: "Apache voting tool" <$issueaddr>
To: $voter
Subject: Apache vote on $issuename
Reply-To: $monitors

EndOutput
    open(INFILE, $issuefile) || die "$pname: cannot open issue file: $!\n";
    print MAIL randomize(<INFILE>);
    close(INFILE);
    &explain_vote(*MAIL, $h1);
    close(MAIL);
}

# ==========================================================================
print "Issue $issuename with hashcode of $monhash\nhas been successfully created.\n";
exit(0);


# ==========================================================================
# ==========================================================================
sub explain_vote {
    local (*FDES, $hashid) = @_;

    print FDES <<"EndOut1";

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

Your voting key for this issue: $hashid

In order to vote, either visit

   https://vote.apache.org/cast/$issuename/$hashid

or use ssh to login to $host and then run

   /home/voter/bin/vote $issuename $hashid "vote"

EndOut1

    if ($selector == 0) {
        print FDES <<"EndYNA";
where "vote" must be replaced by "yes", "no", or "abstain".
EndYNA
    }
    elsif ($vote_type =~ /^stv/i) {
        print FDES <<"EndSTV";
where "vote" must be replaced by a single word containing the
concatenated labels of candidates in the order that you wish them
to be selected.  In other words, if you want to vote for the candidates
labeled [x], [s], and [p], in that order, then your vote should be "xsp".

This election will be decided according to the Single Transferable Vote
rules described at

   http://wiki.apache.org/general/BoardVoting
   http://www.electoral-reform.org.uk/votingsystems/stvi.htm
   http://www.cix.co.uk/~rosenstiel/stvrules/index.htm

for an election with $selector open slots. 

You have one vote.  Use your vote by entering the label of your
first preference candidate followed by, if desired, the label of your
second preference candidate, and so on until you are indifferent about
the remaining candidates.  The sequence of your preferences is crucial.
You should continue to express preferences only as long as you are able
to place successive candidates in order.  A later preference is considered
only if an earlier preference has a surplus above the quota required for
election, or is excluded because of insufficient support.  Under no
circumstances will a later preference count against an earlier preference.

You may list as many candidates as you wish, but no more than once per
vote (e.g., "xsxp" would be rejected).
EndSTV
    }
    else {
        print FDES <<"EndSelect";
where "vote" must be replaced by a single word containing the
concatenated labels of your $selector choices.  In other words,
if you want to vote for the candidates labeled [x], [s], and [p],
then your vote should be "xsp" (order does not matter).
EndSelect
    }

    print FDES <<"EndExplain";
If for some reason you are unable to use ssh to access $host,
then you can vote by proxy: simply send your voting key to some
person with ssh access that you trust, preferably with instructions
on how you wish them to place your vote.

For verification purposes, you will be receiving an e-mail notification
each time your voting key is used.  Repeat votes will be considered
a complete replacement of your prior vote.  Your vote will be
recorded in a tally file and sent to the vote monitors along with
a different unique key, minimizing the chance that the contents of
your vote will be accidentally seen by someone else while associated
to you.  That is why the verification e-mail will only state that you
have voted, rather than including how you voted.

If you have any problems or questions, send a reply to the vote monitors
for this issue: $monitors

EndExplain
}

