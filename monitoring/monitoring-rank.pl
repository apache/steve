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
# 0422f389874d7a8ecfd2fabea0a152ed lagd
# 9c58d57506a17c83b9d4cc8c0ed4a31e lgej
# 9db55691a072f88d79968eed8297dc90 fcaki
# a6d1332887e40af1dd2405cd2abf1e77 glfj
# a9472aa4f7df905173acd8fe2d8edcb2 jkc
# adc9914bb9112d8da4cddd6353e09ef1 eagk
#
# It prints out a file in the format expected by Voting Systems Toolbox
#
#   http://sourceforge.net/projects/votesystem
#
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

print "rank order\n";
print "NAME,  Ken, Justin, Fitz, Dirk, Jim, BenL, Geir, Stefano, Sam, Dims, Greg, Sander\n";
print "LABEL, c,   k,      j,    f,    e,   g,    d,    b,       i,   h,    l,    a\n";

open(INPUT, "$ARGV[0]");

while(<INPUT>) {
  if(/([\w\d]{32})\s([a-m]{1,12})/) {
    @votes = split(//, $2);
    $vstr = join(',', @votes);
    print "$1,$vstr\n";
  }
}
# ============================================================
