#!/usr/bin/perl
# Copyright (C) 2002  The Apache Software Foundation. All rights reserved.
#                     This code is Apache-specific and not for distribution.
# vote
# A program for mostly-anonyous voting.
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
#   o  sends mail to the election monitor(s) indicating the vote that
#      was received and the hashed-hash-id (to identify repeats).
# 
#   o  sends mail to voter indicating that their vote has been received
#      (but not the contents of the vote);
# 
# I do not claim that this is the perfect voting solution.  Some of the
# problems:
# 
#   -  it allows voter and root users the ability to modify
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
$SENDMAIL = '/usr/sbin/sendmail';

$date     = `/bin/date`;
chomp $date;

$homedir  = '/home/voter';
$issuedir = "$homedir/issues";

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
usage: $pname [ group-issue-name [ hash-id [ vote ] ] ]

$pname -- Vote anonymously using the Apache on-line voter process

EndUsage
}

# ==========================================================================
# Get the command-line options and input from the user

$_ = (shift || &get_input_line("the issue name", 1));
if (/^(\w+)-(\d+)-(\w+)$/) {
    $group      = $1;
    $start_date = $2;
    $issue      = $3;
    $issuename  = $_;
}
else { &usage; }

$_ = (shift || &get_input_line("your voter hash-ID", 1));
if (/^(\w+)$/) {
    $vhashid = $1;
}
else { die "Invalid hash-id\n"; }

$_ = (shift || &get_input_line("your vote on issue $issuename", 0));
if (/^(\w+)$/) {
    $vote = $1;
}
else { die "Invalid vote\n"; }

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

# ==========================================================================
# validate vote based on voting style

$typefile = "$issuedir/vote_type";
if (! -e $typefile) { die "$pname: can't find vote_type\n"; }
$vote_type = `$CAT $typefile`;
chomp $vote_type;

if ($vote_type =~ /^YNA$/i) {
    $selector = 0;
    $style = "yes, no, or abstain";
    $vote =~ tr/A-Z/a-z/;
    die "This issue only allows $style as votes\n"
        unless ($vote =~ /^(no|yes|abstain)$/);
}
elsif ($vote_type =~ /^select([1-9])$/i) {
    $selector = $1;
    $style = "select $selector of the identified candidates, labeled [a-z0-9]";
    $vote =~ tr/A-Z/a-z/;
    die "You can only vote for at most $selector candidates\n"
        unless (length($vote) <= $selector);
}
else {
    die "$pname: failed to read vote_type\n";
}

# ==========================================================================
# Recreate the table of voter hash-ids

$issid = &filestuff($issuefile);
foreach $voter (@voters) {
    $h1 = &get_hash_of("$issid:$voter");
    $h2 = &get_hash_of("$issid:$h1");
    $hash2{$voter} = $h2;
    $invert1{$h1} = $voter;
}

$voter = $invert1{$vhashid};
if (!defined($voter))  { die "I don't recognize your voter hash-ID\n"; }

$vhash2 = $hash2{$voter};
if (!defined($vhash2)) { die "I can't find your hashed-hash-ID\n"; }

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

# ==========================================================================
# Send mail to monitors telling them that the issue has been put to
# a vote, including the list of valid hashed hash-ids, sigs of files,
# and the issue info file.

# open (MAIL, ">>debug.txt") || die("cannot send mail: $!\n");
open (MAIL, "|$SENDMAIL -t -f$issueaddr") || die("cannot send mail: $!\n");

print MAIL <<"EndOutput";
To: $monitors
Subject: $issuename

The following vote was received at $date

   issue: $issuename
   voter: $vhash2  vote: $vote

EndOutput

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

print MAIL "Current file digests:\n\n";
foreach $vf (@vfiles) {
    $pf = $vf;
    $pf =~ s/^$homedir\///o;
    print(MAIL &hash_file($vf), ': ', $pf, "\n");
}
close(MAIL);

# ==========================================================================
# Send mail to voter telling them that someone voted using their hash-ID

# open (MAIL, ">>debug.txt") ||
open (MAIL, "|$SENDMAIL -t -f$issueaddr") ||
    die("cannot send mail to $voter: $!\n");

print MAIL <<"EndOutput";
To: $voter\@apache.org
Subject: Recorded your vote on $issuename
Reply-To: $monitors

Somebody (hopefully you or your proxy) has recorded a vote on

   issue: $issuename

using the hash-ID assigned to you.

If you have any problems or questions, send a reply to the vote monitors
for this issue: $monitors

EndOutput
close(MAIL);

# ==========================================================================
print "Mail has been sent to you and the vote monitors.\n";
exit(0);

# ==========================================================================
# ==========================================================================
sub get_input_line {
    local ($prompt, $quit_able) = @_;
    local ($_);

    do {
        print("Enter ", $prompt, $quit_able ? " (q=quit): " : ": ");
        $_ = <STDIN>;
        chomp;
        exit(0) if ($quit_able && /^q$/i);
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
    chomp $rv;
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
    chomp $rv;
    return $rv;
}

