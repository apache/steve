#!/usr/bin/perl
# Copyright (C) 2002  The Apache Software Foundation. All rights reserved.
#                     This code is Apache-specific and not for distribution.
# vote
# A program for almost-anonyous voting.
#
#   o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
#   o  a simple program that takes as arguments an issue name,
#      voter hash-id, and vote (yes/no/abstain or a multi-selection word);
# 
#   o  validates arguments based on type of issue;
# 
#   o  appends timestamp, hashed-hash-id, and vote to the tally;
# 
#   o  sends mail to voter indicating that their vote has been received
#      (but not the contents of the vote);
# 
#   o  sends mail to the election monitor(s) indicating the vote that
#      was received and the hashed-hash-id (to identify repeats).
# 
# I do not claim that this is the perfect voting solution.  Some of the
# problems:
# 
#   -  it allows the sudo users and root users the ability to modify
#      the votes after they have been received, though this should be
#      detected unless they also spoof or intercept mail to the monitors.
# 
#   -  it allows several ways for an observer to connect-the-dots
#      between the voting persons and their hash-id, and thus to their
#      vote, particularly if the observer has access to the mail queue
#      or user command history.
# 
#   -  it allows the sudo users and root users the ability to modify
#      the vote or close_issue commands, changing the results.
# 
# However, these drawbacks are not significantly worse than a
# traditional ballot box and manual counting at a meeting, at least
# when we compare it to the stockholder votes by proxy that are
# commonly done for public companies.  I think this will be sufficient
# to keep votes accurate and anonymous given a trusting environment.
# 
# Originally created by Roy Fielding
#
$ENV{'PATH'}    = '/home/voter/bin:/usr/bin:/usr/sbin:/bin:/sbin';
$ENV{'LOGNAME'} = 'voter';
$ENV{'GROUP'}   = 'voter';
$ENV{'USER'}    = 'voter';
$ENV{'HOME'}    = '/home/voter';
$ENV{'MAIL'}    = '/var/mail/voter';

$ECHO     = '/bin/echo';
$CAT      = '/bin/cat';
$MD5      = '/sbin/md5';
$OPENSSL  = '/usr/bin/openssl';
$TOUCH    = '/usr/bin/touch';
$SENDMAIL = '/usr/sbin/sendmail';

$date     = `/bin/date`;

$homedir  = '/home/voter';
$issuedir = "$homedir/issues";
$host     = 'cvs.apache.org';

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
usage: $pname group-issue-name hash-key vote

$pname -- Vote anonymously on the given issue

EndUsage
}

# ==========================================================================
# Get the command-line options or input from the user

if ($#ARGV != 2) { &usage; }

$_ = shift;
if (/^(\w+)-(\d+)-(\w+)$/) {
    $group      = $1;
    $start_date = $2;
    $issue      = $3;
    $issuename  = $_;
}
else { &usage; }

$_ = shift;
if (/^(\w+)$/) {
    $vhashid = $1;
}
else { &usage; }

$_ = shift;
if (/^(\w+)$/) {
    $vote = $1;
}
else { &usage; }

# ==========================================================================
# Expand and further validate input

@voters = &get_group($group);
if ($#voters < 0) {
    die "$pname: group must be a valid unix group of voters\n";
}
$issueaddr = "voter-$issuename\@apache.org";

$issuedir .= "/$group/$start_date-$issue";
if (! -d $issuedir) { die "$pname: $issuename doesn't exist\n"; }
$closerfile = "$issuedir/closed";
if (-e $closerfile) { die "$pname: $issuename already closed voting\n"; }
$tallyfile = "$issuedir/tally";
if (! -e $tallyfile) { die "$pname: $issuename not yet open to voting\n"; }
$issuefile = "$issuedir/issue";
if (! -e $issuefile) { die "$pname: $issuename lost issue file\n"; }

$monfile = "$issuedir/monitors";
if (! -e $monfile) { die "$pname: can't find monitors\n"; }
$monitors = `$CAT $monfile`;
chomp $monitors;

$stylefile = "$issuedir/vote_type";
if (! -e $stylefile) { die "$pname: can't find vote_type\n"; }
$vote_type = `$CAT $stylefile`;
chomp $vote_type;

if ($vote_type =~ /^YNA$/i) {
    $selector = 0;
    $style = "yes, no, or abstain";
}
elsif ($vote_type =~ /^select([1-9])$/i) {
    $selector = $1;
    $style = "select $selector of the identified candidates, labeled [a-z0-9]";
}
else {
    die "$pname: vote type must be YNA or selectN (N=[1-9])\n";
}

# ==========================================================================
# Recreate the table of voter hash-ids

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
# &debug_hash;

$voter = $invert1{$vhashid};
if (!defined($voter)) { die "I don't recognize your voter hash ID\n"; }

$vhash2 = $hash2{$voter};
if (!defined($vhash2)) { die "I don't recognize your voter hash ID\n"; }

# ==========================================================================
# construct vote entry
$entry = "[$date] $vhash2 $vote\n";

# ==========================================================================
# write vote entry to tally file -- this should be atomic

if (-e $closerfile) { die "$pname: $issuename already closed voting\n"; }

open(TALLY, ">>$tallyfile") || die "$pname: cannot open tally: $!\n";

$len = length($entry);
$off = 0;
do {
    $written = syswrite(TALLY, $entry, $len, $off);
    if (!defined($written)) { die "$pname: cannot write to tally: $!\n"; }
    $len -= $written;
    $off -= $written;
} while ($len > 0);

close(TALLY);

print "Your vote has been accepted on issue $issuename\n";
exit(0);
# ==========================================================================
__END__

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
close(MON);

# ==========================================================================
# Verify with user that the info file is okay before mailing everyone.

print "Here is the content of the issue information file:\n";
print "==============================================================\n";
system($CAT, $issuefile);
print "==============================================================\n";
do {
    $_ = &get_input_line('"ok" to accept or "abort" to delete issue');
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

   /home/voter/bin/close_issue $issuename \\
                               $monhash

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

if ($selector == 0) {
    $explanation = '"yes", "no", or "abstain".' . "\n";
}
else {
    $explanation = <<"EndExplain";
a single word containing the
concatenated labels of your $selector choices.  In other words,
if you want to vote for the candidates labeled [x], [s], and [p],
then your vote should be "xsp" (order does not matter).  The voter
code will not attempt to verify that the labels chosen are valid.
EndExplain
}

while (($voter, $h1) = each %hash1) {
    print "Sending mail to voter: $voter\@apache.org\n";
    print "                hash1: $h1\n";
    open (MAIL, ">>debug.txt") ||
#   open (MAIL, "|$SENDMAIL -t -f$issueaddr") ||
        die("cannot send mail to $voter: $!\n");

    print MAIL <<"EndOutput";
To: $voter\@apache.org
Subject: Apache vote on $issuename
Reply-To: $monitors

EndOutput
    open(INFILE, $issuefile) || die "$pname: cannot open issue file: $!\n";
    print MAIL <INFILE>;
    close(INFILE);

    print MAIL <<"EndOutput";

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

Your voting key for this issue: $h1

In order to vote, use ssh to login to $host and then run

   /home/voter/bin/vote $issuename \\
                        $h1 "vote"

where "vote" must be replaced by $explanation
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

EndOutput
    close(MAIL);
}

# ==========================================================================
print "Issue $issuename has been successfully created.\n";
exit(0);

# ==========================================================================
# ==========================================================================
sub get_input_line {
    local ($prompt) = @_;
    local ($_);

    do {
        print("Enter ", $prompt, " (q=quit): ");
        $_ = <STDIN>;
        chop;
        exit(0) if (/^q$/i);
    } while (/^$/);

    return $_;
}

# ==========================================================================
sub get_group {
    local ($group) = @_;
    local ($name, $passwd, $gid, $members);

    ($name, $passwd, $gid, $members) = getgrnam($group);
    return split(' ', defined($members) ? $members : '');
}

# ==========================================================================
sub filestuff {
    local ($filename) = @_;
    local ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
           $atime,$mtime,$ctime,$blksize,$blocks);

    ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
     $atime,$mtime,$ctime,$blksize,$blocks) = stat($filename);

    return "$ino:$mtime";
}

# ==========================================================================
sub get_hash_of {
    local ($item) = @_;
    local ($rv);

    if (-x $MD5) {
        $rv = `$MD5 -q -s "$item"` || die "$pname: failed md5: $!\n";
    }
    else {
        $rv = `$ECHO "$item" | $OPENSSL md5`
              || die "$pname: failed openssl md5: $!\n";
    }
    chop($rv);
    return $rv;
}

# ==========================================================================
sub hash_file {
    local ($filename) = @_;
    local ($rv);

    if (-x $MD5) {
        $rv = `$MD5 -q "$filename"` || die "$pname: failed md5: $!\n";
    }
    else {
        $rv = `$CAT "$filename" | $OPENSSL md5`
              || die "$pname: failed openssl md5: $!\n";
    }
    chop($rv);
    return $rv;
}

# ==========================================================================
sub debug_hash {
    print "==============================================================\n";
    foreach $voter (@voters) {
        print "$hash1{$voter} $hash2{$voter} $voter\n";
    }
    print "==============================================================\n";
}

