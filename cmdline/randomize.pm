#!/usr/bin/perl
# Copyright (C) 2004  The Apache Software Foundation. All rights reserved.
#                     This code is Apache-specific and not for distribution.
# randomize.pm
# randomize the order in which candidates are listed
#
# candidates are identified with a single alphanumeric character surrounded
# by square brackets as the first non-blank on a line.
#
# candidates are to be listed consecutively, one per line.  If this is
# found not to be the case, NO reordering is performed.
#
# Originally created by Sam Ruby

use strict;

sub randomize {
  my (@prolog, @choices, @epilog);

  push @prolog, shift  while @_ && not $_[0]  =~ /^\s*\[[a-z0-9]\]\s/;
  unshift @epilog, pop while @_ && not $_[-1] =~ /^\s*\[[a-z0-9]\]\s/;
  return @prolog, @_, @epilog if grep !/^\s*\[\S\]\s/, @_;
  push @choices, splice(@_, rand @_, 1) while @_;
  return @prolog, @choices, @epilog;
}

1;
