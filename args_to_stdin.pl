#!/usr/bin/perl -nal

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

# args_to_stdin.pl - prevents vote scripts from exposing
#                    their arguments to `ps` listings by
#                    passing them to stdin instead.
#
# Usage: args_to_stdin.pl <vote.txt

use warnings;

@F or next;

while ($F[-1] =~ /\\$/) {
    chop $F[-1];
    pop @F if $F[-1] eq "";
    defined($_ = <>) or last;
    s/^\s+//;
    push @F, split /\s+/, $_;
}

my $e = shift @F;
die "Can't find executable $e" unless -x $e;
open my $p, "|$e" or die "can't start $e: $!";
print $p $_ for @F;
close $p or warn "can't close $e: $?";
