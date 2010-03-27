#!/usr/bin/perl -T
use strict;
use warnings;
use CGI;
use CGI::Carp qw/fatalsToBrowser/;
use Digest::MD5;

BEGIN {
    push @INC, "/home/voter/bin";
}
use randomize;


my $VOTE_TOOL = "/home/voter/bin/vote";
my $VOTE_TMPDIR = "/home/voter/tmp";
my $VOTE_ISSUEDIR = "/home/voter/issues";

$ENV{PATH_INFO} =~ m!^/(\w+)-(\d+-\w+)/([0-9a-f]{32})$!
    or die "Malformed URL\n";
my ($group, $issue, $hash) = ($1, $2, $3);

my $voter = fetch_voter($group, $issue, $hash)
    or die "Invalid URL\n";
my ($type, @valid_vote) = fetch_type_info($group, $issue)
    or die "Can't identify issue type!\n";

if ($ENV{REQUEST_METHOD} eq "GET" or $ENV{REQUEST_METHOD} eq "HEAD") {

    my $issue_path = "$VOTE_ISSUEDIR/$group/$issue/issue";
    open my $fh, $issue_path or die "Can't open issue: $!\n";
    read $fh, my $issue_content, -s $fh;
    close $fh;

    $issue_content = join "\n", randomize split /\n/, $issue_content;
    $issue_content .= "\n"; # split knocks off the last newline

    print "Content-Type: text/html\n\n";

    if ($type eq "yna") {
        print yna_form($voter, $issue_content);
    }
    elsif ($type =~ /^stv([1-9])$/) {
        print stv_form($1, $voter, $issue_content);
    }
    elsif ($type =~ /^select([1-9])$/) {
        print select_form($1, $voter, $issue_content);
    }

    exit;

} elsif ($ENV{REQUEST_METHOD} eq "POST") {
    my $q = CGI->new;
    my $vote = $q->param("vote");
    die "Vote undefined\n" unless defined $vote;
    $vote =~ tr/A-Z/a-z/;

    if ($type eq "yna") {
        grep $_ eq $vote, @valid_vote or die "Invalid yna vote: $vote\n";
    }
    elsif ($type =~ /([1-9])$/) {
        my $selection = $1;
        if ($type =~ /^select/) {
            length($vote) <= $selection
                or die "Too many candidates: only select up to $selection: $vote\n";
        }
        my $char_class = "[" . join("",@valid_vote) . "]";
        $vote =~ /^$char_class+$/
            or die "$type vote out of range (no such candidate): $vote\n";
        my %uniq;
        @uniq{split //, $vote} = ();
        length($vote) == keys %uniq
            or die "Duplicate candidates in $type vote: $vote\n";
    }

    # vote is valid, time to execute the program...

    umask 077;
    local %ENV;

    my $tmpfile = "$VOTE_TMPDIR/$issue.$$";
    my $cmd = "$VOTE_TOOL > $tmpfile 2>&1";
    open my $vote_tool, "| $cmd"
        or die "Can't popen '$cmd': $!\n";

    local $SIG{TERM} = local $SIG{INT} = local $SIG{HUP} = local $SIG{PIPE}
        = sub {
            unlink $tmpfile;
            die "SIG$_[0] caught\n";
        };

    print $vote_tool "$group-$issue\n";
    print $vote_tool "$hash\n";
    print $vote_tool "$vote\n";

    close $vote_tool;
    my $vote_status = $?;
    my $vote_log;

    if (open my $fh, $tmpfile) {
        read $fh, $vote_log, -s $fh;
        close $fh;
        unlink $tmpfile;
    }
    else {
        unlink $tmpfile;
        die "Couldn't open $tmpfile: vote status=$vote_status: $!\n";
    }

    print <<EoVOTE;
Content-Type: text/html

<html>
<head>
<title></title>
</head>
<body>
<h1>Vote results for &lt;$voter&gt; on $group-$issue...</h1>
<h2>Vote Tool Exit Status: $vote_status (0 means success!)</h2>
<textarea>$vote_log</textarea>
</body>

EoVOTE

    exit;

} else {
    die "Unsupported method $ENV{REQUEST_METHOD}\n";
}

sub fetch_type_info {
    my ($group, $issue) = @_;
    open my $fh, "$VOTE_ISSUEDIR/$group/$issue/vote_type" or return;
    chomp(my @data = <$fh>);
    return @data;
}


sub fetch_voter {
    my ($group, $issue, $hash) = @_;
    my $issue_id = eval { filestuff("$VOTE_ISSUEDIR/$group/$issue/issue") }
        or return;
    for my $voter (eval { get_group("$VOTE_ISSUEDIR/$group/voters") }) {
        return $voter if get_hash_of("$issue_id:$voter") eq $hash;
    }
    return;
}

sub get_hash_of {
    my ($item) = @_;
    my $md5 = Digest::MD5->new;
    $md5->add($item);
    return $md5->hexdigest;
}


sub get_group {
    my ($groupfile) = @_;
    local $_;
    my @rv;

    open(my $INFILE, $groupfile) || die "cannot open $groupfile: $!\n";
    while (<$INFILE>) {
        chomp;
        s/#.*$//;
        s/\s+$//;
        s/^\s+//;
        next if (/^$/);
        push(@rv, $_);
    }
    close($INFILE);
    return @rv;
}

sub filestuff {
    my ($filename) = @_;
    my ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
        $atime,$mtime,$ctime,$blksize,$blocks);

    ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
     $atime,$mtime,$ctime,$blksize,$blocks) = stat($filename)
         or die "Can't stat $filename: $!\n";

    return "$ino:$mtime";
}

sub yna_form {
    my ($voter, $issue_content) = @_;

    my $html = <<EoYNA;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content
</pre>
EoYNA
}

sub stv_form {
    my ($num, $voter, $issue_content) = @_;

    my $html = <<EoSTV;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content
</pre>
EoSTV
}

sub select_form {
    my ($num, $voter, $issue_content) = @_;

    my $html =  <<EoSELECT;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content
</pre>
EoSELECT
}
