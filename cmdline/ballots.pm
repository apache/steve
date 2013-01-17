#!/usr/bin/perl
# Copyright (C) 2005  The Apache Software Foundation. All rights reserved.
#                     This code is Apache-specific and not for distribution.
# ballots.pm
# return the ballot identifiers for each candidate in an issue.
#
# candidates are identified with a single alphanumeric character surrounded
# by square brackets as the first non-blank on a line.
#
# candidates are to be listed consecutively, one per line.
#

use strict;

sub ballots{
  my (@ballots);

  shift  while @_ && not $_[0]  =~ /^\s*\[[a-z0-9]\]\s/;
  for (@_) {
    if (/^\s*\[([a-z0-9])\]\s/) {
      push @ballots, "$1\n";
    } else {
      last;
    }
  }
  return @ballots;
}

1;
