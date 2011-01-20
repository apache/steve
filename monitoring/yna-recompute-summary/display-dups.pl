#!/usr/bin/perl -w
use strict;

my $label = shift // "(stdin)";
my %votes;
my %result;

while (<>) {
  my (undef, $hash, undef, $vote) = split;
  $votes{$hash} .= substr($vote, 0, 1);
  $result{$vote}++;
}

while (my ($h, $v) = each %votes) {
  print "WARNING: $label: '$h' voted '$v'\n" if $v =~ /../;
}

my $yesno = ($result{yes} > $result{no}) ? "YES" : "NO";
my $margin = ($result{yes} - $result{no});

print "RESULTS: $label: $yesno (margin=$margin; +$result{yes}, -$result{no}, =$result{abstain})\n";
warn "Unknown keys found" if grep { ! /^(yes|no|abstain)$/ } keys %result;
