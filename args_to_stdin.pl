#!/usr/bin/perl -nal

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
