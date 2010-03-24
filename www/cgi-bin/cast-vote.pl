#!/usr/bin/perl -T
use strict;
use warnings;
use CGI;
use CGI::Carp qw/fatalsToBrowser/;

my $VOTE_TOOL = "/home/voter/bin/vote";
my $VOTE_TMPDIR = "/home/voter/tmp";
my $VOTE_DATADIR = "/home/voter/issues";

$ENV{PATH_INFO} =~ m!^/([\w-]+)/([0-9a-f]{32})/(yna|stv[1-9]|select[1-9])$!
    or die "Invalid path";
my ($issue, $hash, $type) = ($1, $2, $3);


if ($ENV{REQUEST_METHOD} eq "GET" or $ENV{REQUEST_METHOD} eq "HEAD") {

    my $issue_path = "$VOTE_DATADIR/$issue/issue";
    $issue_path =~ s!\-!/! or die "Invalid issue path";
    open my $fh, $issue_path or die "Can't open issue: $!";
    read $fh, my $issue_content, -s $fh;
    close $fh;

    print "Content-Type: text/html\n\n";

    if ($type eq "yna") {
        print <<EoYNA;

<pre>
$issue_content
</pre>
EoYNA
    }
    elsif ($type =~ /^stv[1-9]$/) {
        print <<EoSTV;

<pre>
$issue_content
</pre>
EoSTV
    }
    elsif ($type =~ /^select[1-9]$/) {
        print <<EoSELECT;

<pre>
$issue_content
</pre>
EoSELECT
    }

    exit;

} elsif ($ENV{REQUEST_METHOD} eq "POST") {
    my $q = CGI->new;
    my $vote = $q->param("vote");
    die "Vote undefined" unless defined $vote;

    local %ENV;

    my $tmpfile = "$VOTE_TMPDIR/$issue.$$";
    my $cmd = "$VOTE_TOOL > $tmpfile 2>&1";
    open my $voter_tool, "| $cmd"
        or die "Can't popen '$cmd': $!";

    local $SIG{TERM} = local $SIG{INT} = local $SIG{HUP} = sub {
        unlink $tmpfile;
        die "SIG$_[0] caught";
    };

    print $voter_tool "$issue\n";
    print $voter_tool "$hash\n";
    print $voter_tool "$vote\n";

    my $vote_status = close $voter_tool;
    my $vote_log;

    if (open my $fh, $tmpfile) {
        read $fh, $vote_log, -s $fh;
        close $fh;
        unlink $tmpfile;
    }
    else {
        unlink $tmpfile;
        die "Couldn't open $tmpfile: vote status=$vote_status: $!";
    }

    print <<EoVOTE;
Content-Type: text/html

<html>
<head>
<title></title>
</head>
<body>
<h2>Vote Tool Exit Status: $vote_status (0 means success!)</h2>
<textarea>$vote_log</textarea>
</body>

EoVOTE

    exit;

} else {
    die "Unsupported method $ENV{REQUEST_METHOD}";
}
