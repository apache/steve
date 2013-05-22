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
# check_quorum
# A program for checking if a closed issue reached quorum and
# providing a sorted list of people whose vote was received.
#
#   o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
#   o  takes as argument an issue name;
# 
#   o  checks to be sure the issue has closed (to prevent abuse);
# 
#   o  sends mail to the election monitor(s) indicating the sorted
#      list of voted addresses and ratio of votes cast to voters in group.
# 
# Originally created by Roy Fielding
#
$ECHO     = '/bin/echo';
$CAT      = '/bin/cat';
$MD5      = '/sbin/md5';
$OPENSSL  = '/usr/bin/openssl';
$SENDMAIL = '/usr/sbin/sendmail';

$homedir  = '/home/voter';
$issuedir = "$homedir/issues";

$ENV{'PATH'}    = "$homedir/bin:/usr/bin:/usr/sbin:/bin:/sbin";
$ENV{'LOGNAME'} = 'voter';
$ENV{'GROUP'}   = 'voter';
$ENV{'USER'}    = 'voter';
$ENV{'HOME'}    = "/home/voter";
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
usage: $pname [ group-issue-name ]

$pname -- Check for quorum by listing the voters on a closed issue

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

# ==========================================================================
# Expand and further validate input

$votersfile = "$issuedir/$group/voters";
@voters = &get_group($votersfile);
if ($#voters < 0) {
    die "$pname: group $group must be an existing voter group\n";
}

$issueaddr = 'voter@apache.org';

$issuedir .= "/$group/$start_date-$issue";
if (! -d $issuedir) { die "$pname: $issuename doesn't exist\n"; }
$closerfile = "$issuedir/closed";
if (! -e $closerfile) { die "$pname: $issuename has not closed voting\n"; }
$tallyfile = "$issuedir/tally";
if (! -e $tallyfile) { die "$pname: $issuename not yet open to voting\n"; }
$issuefile = "$issuedir/issue";
if (! -e $issuefile) { die "$pname: $issuename lost issue file\n"; }

$monfile = "$issuedir/monitors";
if (! -e $monfile) { die "$pname: can't find monitors\n"; }
$monitors = `$CAT $monfile`;
chomp $monitors;

# ==========================================================================
# Recreate the table of voter hash-ids

$issid = &filestuff($issuefile);
foreach $voter (@voters) {
    $h1 = &get_hash_of("$issid:$voter");
    $h2 = &get_hash_of("$issid:$h1");
    $invert2{$h2} = $voter;
}

# ==========================================================================
# Read the tally file

@voted = ();

%tally = &read_tally($tallyfile);
foreach $vkey (keys(%tally)) {
    push(@voted, $invert2{$vkey} || "Yikes, bad key: $vkey");
}
$num_voted = scalar(keys(%tally));
$num_group = scalar(@voters);
$pct_voted = int( ($num_voted * 100) / $num_group );

# ==========================================================================
# Send mail to monitors telling them who voted on the issue

# open (MAIL, ">>debug.txt") || die("cannot send mail: $!\n");
open (MAIL, "|$SENDMAIL -t -f$issueaddr") || die("cannot send mail: $!\n");

print MAIL <<"EndOutput";
From: "Apache voting tool" <$issueaddr>
To: $monitors
Subject: voters on $issuename

Votes on issue $issuename were received from the following voters,
representing $num_voted out of the $num_group eligible voters ($pct_voted\%).

EndOutput

foreach $vf (sort(@voted)) {
    print(MAIL "   ", $vf, "\n");
}
print(MAIL "\nTotal: $num_voted of $num_group ($pct_voted\%)\n");
close(MAIL);

# ==========================================================================
print("Quorum information has been sent to the monitors.\n");
print("Total: $num_voted of $num_group ($pct_voted\%)\n");
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
    local ($groupfile) = @_;
    local ($_, @rv);

    open(INFILE, $groupfile) || die "$pname: cannot open $groupfile: $!\n";
    while ($_ = <INFILE>) {
        chomp;
        s/#.*$//;
        s/\s+$//;
        s/^\s+//;
        next if (/^$/);
        push(@rv, $_);
    }
    close(INFILE);
    return @rv;
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
sub read_tally {
    local ($filename) = @_;
    local ($_, %rv);

    %rv = ();

    open(INFILE, $filename) || die "$pname: cannot open $filename: $!\n";
    while ($_ = <INFILE>) {
        chomp;
        if (/\] (\S+) (\S+)$/o) {
            $rv{$1} = $2;
        }
        else {
            warn "Invalid vote in tally: $_";
        }
    }
    close(INFILE);

    return %rv;
}
