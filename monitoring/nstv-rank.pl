#!/usr/bin/perl
# ============================================================
#
# SCRIPT NAME: rank
#
# This script takes in files in the form
#
# voter vote
#
# e.g
#
# [2006/06/13 18:22:30] 0422f389874d7a8ecfd2fabea0a152ed lagd
# [2006/06/13 18:23:15] 9c58d57506a17c83b9d4cc8c0ed4a31e lgej
# [2006/06/13 18:28:27] 9db55691a072f88d79968eed8297dc90 fcaki
# [2006/06/13 19:01:13] a6d1332887e40af1dd2405cd2abf1e77 glfj
# [2006/06/13 19:22:45] a9472aa4f7df905173acd8fe2d8edcb2 jkc
# [2006/06/13 20:42:33] adc9914bb9112d8da4cddd6353e09ef1 eagk
#
# and, by default, prints out a file in the format expected by
# Voting Systems Toolbox:
#
#   http://sourceforge.net/projects/votesystem
#
# It can also print out a file in BLT format, via the '-b' argument.
#
# It takes an optional argument, '-d', which instructs the script
# to only output the last vote per ID, thus ignoring previous
# votes. ONLY use this if you are positive that the input
# file is in time-stamped order with newer votes appended to
# the end! NOTE: The voter tool does this automatically!
#
#### VoteMain instructions ####
# After installing Voting Systems Toolbox, you can execute the 'VoteMain'
# program as
#
#   java -cp Vote-0-4.jar VoteMain -system stv-meek -seats 9 outputFile
#
# where outputFile is the result of this script (rank).
#
# The output of  'VoteMain' program is the result of the elections.
#
# Note that the 'VoteMain' program can detect duplicate votes, as well as votes
# with incorrect labels.

use Getopt::Std;
getopts('db');
if ($opt_d) {
  $handle_dups = 1;
}

%nominees = (
 'a', 'Brett',
 'b', 'Greg',
 'c', 'Jim',
 'd', 'Geir',
 'e', 'Sam',
 'f', 'Bertrand',
 'g', 'Henning',
 'h', 'J Aaron',
 'i', 'Justin',
 'j', 'William',
 'k', 'Sander',
 'l', 'Craig',
 );

@invalids = ();
@raw = ();
@nomkeys = sort keys %nominees;
$numseats = 9;

open(INPUT, "$ARGV[0]");

while(<INPUT>) {
  chomp;
  if(/\[.{19}\]\s([\w\d]{32})\s([a-m]{1,12})/) {
    @votes = split(//, $2);
    $vstr = join(',', @votes);
    if ($handle_dups) {
      $votes{$1} = $vstr;
    } else {
      push (@raw, "$1,$vstr");
    }
  } else {
      push(@invalids, $_);
  }
}

if ($opt_b) {

  $numcands = @nomkeys;
  print "$numcands $numseats\n";
  if ($handle_dups) {
    foreach $id (keys %votes) {
      print "1 ";
      foreach $vote (split(/,/, $votes{$id})) {
         $value = ord($vote) - ord('a') + 1;
         print "$value ";
       }
       print "0\n";
    }
  } else {
    foreach $id (@raw) {
      ($dummy, $cast) = split(/,/,$id, 2);
      print "1 ";
      foreach $vote (split(/,/, $cast)) {
         $value = ord($vote) - ord('a') + 1;
         print "$value ";
       }
       print "0\n";
    }
  }
  print "0\n";
  foreach $id (@nomkeys) {
    print "\"$nominees{$id}\"\n";
  }
  print "\"ASF STV Board Election\"\n";
  
} else {

  print "rank order\n";
  print "NAME, ";
  foreach $id (@nomkeys) {
    if ($id ne 'a') {
      print ",";
    }
    printf ("%10.10s", $nominees{$id});
  }
  print "\n";
  print "LABEL,";
  foreach $id (@nomkeys) {
    if ($id ne 'a') {
      print ",";
    }
    printf ("%10.10s", $id);
  }
  print "\n";

  if ($handle_dups) {
    foreach $id (keys %votes) {
      print "$id,$votes{$id}\n";
    }
  } else {
    foreach $id (@raw) {
      print "$id\n";
    }
  }
}
if (@invalids) {
    print "\n### Input had invalid entries! ###\n";
    foreach $bad (@invalids) {
        print "   $bad\n";
    }
}
# ============================================================
