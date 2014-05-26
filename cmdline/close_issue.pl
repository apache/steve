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
# close_issue.pl
#   o  must be run by voter user (see wrapsuid.c for setuid wrapper);
#   o  accepts issue name and monitor hash-ID as arguments;
#   o  sets a marker indicating no more votes accepted for issue;
#   o  reads in tally, counting only last recorded vote per hashed-hash-id;
#   o  mails summary to election monitor(s)
#   o  [maybe] creates an HTML summary of results as
#         /home/voter/public_html/issue_nnnnnn.html
#
# Originally created by Roy Fielding
#

BEGIN {
    unshift @INC, "/home/voter/bin";
}

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
usage: $pname [ group-issue-name [ hash-id ] ]

$pname -- Close voting on an issue

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

$_ = (shift || &get_input_line("your monitor hash-ID", 1));
if (/^(\w+)$/) {
    $mhashid = $1;
}
else { die "Invalid hash-ID\n"; }

# ==========================================================================
# Expand and further validate input

$votersfile = "$issuedir/$group/voters";

$issueaddr = 'voter@apache.org';

$issuedir .= "/$group/$start_date-$issue";
if (! -d $issuedir) { die "$pname: $issuename doesn't exist\n"; }
$tallyfile = "$issuedir/tally";
if (! -e $tallyfile) { die "$pname: $issuename not yet open to voting\n"; }
$issuefile = "$issuedir/issue";
if (! -e $issuefile) { die "$pname: $issuename lost issue file\n"; }

$monfile = "$issuedir/monitors";
if (! -e $monfile) { die "$pname: can't find monitors\n"; }
$monitors = `$CAT $monfile`;
chomp $monitors;

$typefile = "$issuedir/vote_type";

# ==========================================================================
# Recreate the monitor hash-id

$issid = &filestuff($issuefile);
$monhash = &get_hash_of("$issid:$monitors");

if ($mhashid ne $monhash) { die "I don't recognize your hash-ID\n"; }

# ==========================================================================
# Indicate that voting is now closed

$closerfile = "$issuedir/closed";
system($TOUCH, $closerfile);

# ==========================================================================
# Send mail to monitors telling them that the issue has been closed
# and enclose the final tally

# open (MAIL, ">>debug.txt") || die("cannot send mail: $!\n");
open (MAIL, "|$SENDMAIL -t -f$issueaddr") || die("cannot send mail: $!\n");

print MAIL <<"EndOutput";
From: "Apache voting tool" <$issueaddr>
To: $monitors
Subject: Final tally for $issuename

Issue $issuename is now closed.  The summary is not yet implemented.

Here are the raw collected results -- remember to remove old votes from
those with duplicate entries before counting them.

EndOutput

open(TALLY, $tallyfile) || die "$pname: cannot open tally file: $!\n";
print MAIL <TALLY>;
close(TALLY);

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

print MAIL "\nCurrent file digests:\n\n";
foreach $vf (@vfiles) {
    $pf = $vf;
    $pf =~ s/^$homedir\///o;
    print(MAIL &hash_file($vf), ': ', $pf, "\n");
}
close(MAIL);

# ==========================================================================
print "Issue closed.  Mail has been sent to the vote monitors.\n";
exit(0);

