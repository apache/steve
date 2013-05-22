#!/usr/bin/perl -T
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
