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
# votegroup
# A program for creating a list of voters in the given issue group
#
# o  must be run by voter user (see wrapsuid.c for setuid wrapper)
#
# o  creates a group directory (/home/voter/issues/group/),
#    and adds to it a "voters" file containing a list of e-mail addresses.
#
# Originally created by Roy Fielding
#
require "getopts.pl";
use steve;

$ENV{'PATH'} = "$homedir/bin:/usr/bin:/usr/sbin:/bin:/sbin";

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
usage: $pname [-h] [-b] [-g group] [-f votersfile]

$pname -- Make a group of voters for an on-line, anonymous voting process

Options:
     -h  (help) -- just display this message and quit
     -b  (batch) -- batch processing: assume 'ok' unless errors
     -g  group  -- create the named group of voters
     -f  file   -- contains the list of voter e-mail addresses, one per line

EndUsage
}

# ==========================================================================
# Get the command-line options or input from the user

undef $opt_h;
undef $opt_b;

if (!(&Getopts('hbg:f:')) || defined($opt_h)) { &usage; }

if (defined($opt_g)) {
    $group = $opt_g;
}
else {
    $group = &get_input_line("group name for the voters", 1);
}
if ($group !~ /^\w+$/) {
    die "$pname: group name must be an alphanumeric token\n";
}

if (defined($opt_f)) {
    $infofile = $opt_f;
}
else {
    $infofile = &get_input_line("file pathname of voter e-mail addresses", 1);
}
if (!(-e $infofile)) {
    die "$pname: voters file does not exist: $infofile\n";
}
if ($infofile =~ /(\/etc\/|$issuedir)/) {
    die "$pname: forbidden to read files in that directory\n";
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
    print "Updating existing voting group: $group\n";
}
else {
    print "Creating new voting group: $group\n";
    mkdir($issuedir, 0700) || die "$pname: cannot mkdir $issuedir: $!\n";
}

@voters = &get_group($infofile);
if ($#voters < 0) {
    die "$pname: no valid e-mail addresses were found\n";
}

# ==========================================================================
# Verify with user that the voters file is okay

print "Here is the list of voter e-mail addresses:\n";
print "==============================================================\n";
foreach $voter (@voters) {
    print $voter, "\n";
    $hash1{$voter} = 1;
}
print "==============================================================\n";

$dupes = scalar(@voters) - scalar(keys(%hash1));
if ($dupes != 0) {
    die "$pname: $dupes duplicate voters must be removed from the list\n";
}
do {
    $_ = ($batch ? "ok" : &get_input_line('"ok" to accept or "abort" to exit', 0));
    if (/^abort$/i) {
        exit(1);
    }
} until (/^ok/i);

# ==========================================================================
# Diff an existing voters file

$votersfile = "$issuedir/voters";

if (-e $votersfile) {
    print "Differences from existing list of voters:\n";
    print "==============================================================\n";
    system($DIFF, "-u", $votersfile, $infofile);
    print "==============================================================\n";
    do {
        $_ = ($batch ? "ok" : &get_input_line('"ok" to accept or "abort" to exit', 0));
        if (/^abort$/i) {
            exit(1);
        }
    } until (/^ok/i);
    system($MV, "-f", $votersfile, "$votersfile.old");
}

# ==========================================================================
# Create voters file

open(ISF, ">$votersfile") || die "$pname: cannot write to voters file: $!\n";
open(INFILE, $infofile) || die "$pname: cannot read voters file: $!\n";
print ISF <INFILE>;
close(INFILE);
close(ISF);

# ==========================================================================
print "Voting group $group has been successfully created.\n";
$pf = $votersfile;
$pf =~ s/^$homedir\///o;
print &hash_file($votersfile), ': ', $pf, "\n";

exit(0);

