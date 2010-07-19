#!/usr/bin/perl -T

#
# redirect.pl - simple redirect CGI script
#

use strict;
use warnings;
use CGI;
use CGI qw/fatalsToBrowser/;

my $q = CGI->new;
my $uri = $q->param("uri") or die "Can't find uri param";
print $q->redirect(-uri => $uri, -status => 301);
exit;
