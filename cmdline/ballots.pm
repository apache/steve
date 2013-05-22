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
