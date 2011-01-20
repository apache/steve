#!/usr/bin/perl -w
use strict;

my $maildir = (shift or '/tmp/votem/wd');
die "argv[1] = /PATH/TO/MAILDIR" unless -d $maildir;

while (<>) {
  my $issuename = $_;
  chomp $issuename;
  my $resultsfile = ".results.$issuename";
  unlink $resultsfile or die "unlink: $!"
    if -e $resultsfile;
  open my $grep, "-|", "grep -Rl 'Subject: $issuename' $maildir/" or die "open: $!";
  while (defined (my $fname = <$grep>)) {
    chomp $fname;
    system("grep 'vote: ' $fname >> $resultsfile") == 0 or die "system($?): $!";
  }
}
