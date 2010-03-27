#!/usr/bin/perl
# Copyright (C) 2003  The Apache Software Foundation. All rights reserved.
#                     This code is Apache-specific and not for distribution.
# reminder.pl
# A program for reminding a voter about their voting key
#   o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#   o  a simple program that takes as arguments an issue name and voter
#   o  sends mail to voter repeating the vote instructions
# 
# Originally created by Roy Fielding
#
use randomize;

$ECHO     = '/bin/echo';
$CAT      = '/bin/cat';
$MD5      = '/sbin/md5';
$OPENSSL  = '/usr/bin/openssl';
$SENDMAIL = '/usr/sbin/sendmail';

$homedir  = '/home/voter';
$issuedir = "$homedir/issues";
$host     = 'people.apache.org';

$ENV{'PATH'}    = '$homedir/bin:/usr/bin:/usr/sbin:/bin:/sbin';
$ENV{'LOGNAME'} = 'voter';
$ENV{'GROUP'}   = 'voter';
$ENV{'USER'}    = 'voter';
$ENV{'HOME'}    = '/home/voter';
$ENV{'MAIL'}    = '/var/mail/voter';

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
usage: $pname [ group-issue-name [ voter ] ] ]

$pname -- Remind a voter of their voting key for the given issue

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

$_ = (shift || &get_input_line("the voter's e-mail address", 1));
if (/^(\S+\@\S+)$/) {
    $voter = $1;
}
else { die "Invalid voter\n"; }

# ==========================================================================
# Check to see if the voter is in the voting group

if (! &found_in_group($voter, "$issuedir/$group/voters")) {
    die "$voter is not in group $group\n";
}

# ==========================================================================
# Expand and further validate input

$issueaddr = 'voter@apache.org';

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

$typefile = "$issuedir/vote_type";
if (! -e $typefile) { die "$pname: can't find vote_type\n"; }
$vote_type = (`$CAT $typefile`)[0];
chomp $vote_type;

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
    $style = "select $selector of the identified candidates, labeled [a-z0-9]";
}
else {
    die "$pname: failed to read vote_type\n";
}

# ==========================================================================
# Recreate the table of voter hash-ids

$issid = &filestuff($issuefile);
$h1 = &get_hash_of("$issid:$voter");

# ==========================================================================
# Send mail to voter telling them that the issue has been put to vote,
# including the info file and their commands.

########################################### for debugging
#   print "                hash1: $h1\n";
#   open (MAIL, ">>debug.txt") ||
########################################### replace next line
open (MAIL, "|$SENDMAIL -t -f$issueaddr") ||
    die("cannot send mail to $voter: $!\n");

print MAIL <<"EndOutput";
From: "Apache voting tool" <$issueaddr>
To: $voter
Subject: Reminder: Apache vote on $issuename
Reply-To: $monitors

EndOutput
open(INFILE, $issuefile) || die "$pname: cannot open issue file: $!\n";
print MAIL randomize(<INFILE>);
close(INFILE);
&explain_vote(*MAIL, $h1);
close(MAIL);

# ==========================================================================
print "Sent mail to voter: $voter\n";
exit(0);


# ==========================================================================
# ==========================================================================
sub explain_vote {
    local (*FDES, $hashid) = @_;

    print FDES <<"EndOut1";

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
APACHE VOTE REMINDER:

Your voting key for this issue: $hashid

In order to vote, use ssh to login to $host and then run

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

   http://wiki.apache.org/incubator/BoardElectionVoteCounting
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
sub found_in_group {
    local ($voter, $groupfile) = @_;
    local ($_);

    open(INFILE, $groupfile) || return 0;
    while ($_ = <INFILE>) {
        chomp;
        s/#.*$//;
        s/\s+$//;
        s/^\s+//;
        if ($_ eq $voter) {
            close(INFILE);
            return 1;
        }
    }
    close(INFILE);
    return 0;
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

