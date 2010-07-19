#!/usr/bin/perl -T

#
# redirect.pl - simple redirect CGI script that changes the referer header
#

use strict;
use warnings;
use CGI;
use CGI::Carp qw/fatalsToBrowser/;

my $q = CGI->new;
my $uri = $q->param("uri") or die "Can't find uri param";
print $q->header;
print <<EOT;
<html>
<head>
<meta http-equiv="refresh" content="0;url=$uri" />
</head>
<body>
Redirecting to $uri ...
</body>
</html>
EOT
exit;
