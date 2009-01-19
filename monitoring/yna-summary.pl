#!/usr/bin/perl
# ============================================================
#
# SCRIPT NAME: yna-summary
#
# This script takes in files in the form sent by the
# voter tool final summary Email
#
# e.g
# Issue members200606-20060613-foobar is now closed.  The summary is not yet implemented.
#
# Here are the raw collected results -- remember to remove old votes from
# those with duplicate entries before counting them.
#
# [2006/06/13 18:22:30] 0422f389874d7a8ecfd2fabea0a152ed yes
# [2006/06/13 18:23:15] 9c58d57506a17c83b9d4cc8c0ed4a31e abstain
# [2006/06/13 18:28:27] 9db55691a072f88d79968eed8297dc90 no
# [2006/06/13 19:01:13] a6d1332887e40af1dd2405cd2abf1e77 yes
# [2006/06/13 19:22:45] a9472aa4f7df905173acd8fe2d8edcb2 yes
# [2006/06/13 20:42:33] adc9914bb9112d8da4cddd6353e09ef1 abstain
#
# ...
#
# And produces a summary of total votes, the number of
# dups and the vote summaries themselves.
#
# It is very dependent on the format of the Final Tally
# Email that comes from the voter tool and is
# designed to work on the full email message.
#
# This means you can concat all the final tallies
# together in one big file and this tool will
# correctly parse the whole shebang for you.
#

open(INPUT, "$ARGV[0]");

while(<INPUT>) {
  chomp;
  # Assumes standard format of closed email
  if (/Issue ([^-]*)-[^-]*-(\w*) is now closed/) {
    $issuename = "$1 - $2";
    %votes = ();
    $dups{$issuename} = 0;
    $yes = 0; $no = 0; $abstain = 0; $total = 0;
    next;
  }
  #     [2006/06/13 17:54:23] 4db08a9e058fa8e4742f1f05cd32e409 yes
  if (/\[.{19}\]\s([\w\d]{32})\s([a-z]{1,12})/) {
    if ($votes{$1} ne "") {
      $dups{$issuename}++;
    }
    $votes{$1} = $2;
    next;
  }
  if (/Current file digests:/) {
    foreach $id (keys %votes) {
      $total++;
      #print "$id, $votes{$id} \n";
      if ($votes{$id} eq 'yes') { $yes++; }
      if ($votes{$id} eq 'no') { $no++; }
      if ($votes{$id} eq 'abstain') { $abstain++; }
    }
    if ($yes > $no) {
        $elected = "(elected)";
    } else {
        $elected = "(NOT ELECTED)";
    }
    print "Issue: $issuename: Total: $total ($dups{$issuename}), Yes: $yes, No: $no, Abstain: $abstain    $elected\n";
    next;
  }
}

# ============================================================
