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

    open my $fh, "$VOTE_ISSUEDIR/$group/$issue/issue"
        or die "Can't open issue: $!\n";
    read $fh, my $issue_content, -s $fh;
    close $fh;

    $issue_content = join "\n", randomize split /\n/, $issue_content;
    $issue_content .= "\n"; # split knocks off the last newline

    open $fh, "$VOTE_ISSUEDIR/$group/$issue/monitors"
        or die "Can't open monitor file: $!\n";
    read $fh, my $monitors, -s $fh;
    close $fh;

    my $trailer = <<EOT;
If for some reason you are unable to fill out the form and submit it,
then you can vote by proxy: simply send this URL to some Apache committer
that you trust, preferably with instructions on how you wish them to
place your vote.  DO NOT DISCLOSE THIS URL TO ANYONE ELSE, AS THEY
WILL BE ABLE TO ACT AS YOUR PROXY AND CAST VOTES ON YOUR BEHALF IF
YOU DO.

For verification purposes, you will be receiving an e-mail notification
each time your voting key is used.  Repeat votes will be considered
a complete replacement of your prior vote.  Your vote will be
recorded in a tally file and sent to the vote monitors along with
a different unique key, minimizing the chance that the contents of
your vote will be accidentally seen by someone else while associated
to you.  That is why the verification e-mail will only state that you
have voted, rather than including how you voted.

If you have any problems or questions, send a reply to the vote monitors
for this issue: $monitors
EOT

    print "Content-Type: text/html\n\n";

    if ($type eq "yna") {
        print yna_form($voter, $issue_content, $trailer);
    }
    elsif ($type =~ /^stv([1-9])$/) {
        print stv_form($1, $voter, $issue_content, $trailer);
    }
    elsif ($type =~ /^select([1-9])$/) {
        print select_form($1, $voter, $issue_content, $trailer);
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
    my ($voter, $issue_content, $trailer) = @_;

    my $html = <<EoYNA;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

To cast your vote, select yes, no, or abstain from the form below and click
on the "Submit" button.

$trailer
</pre>
EoYNA
}

sub stv_form {
    my ($num, $voter, $issue_content, $trailer) = @_;

    my $html = <<EoSTV;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

To cast your vote, fill in the form entry for your vote below with a
single word containing the concatenated labels of the candidates in the
order that you wish them to be selected.  In other words, if you want to
vote for the candidates labeled [x], [s], and [p], in that order, then
your vote should be "xsp".

Then click on the "Submit" button to ultimately cast your vote.

This election will be decided according to the Single Transferable Vote
rules described at

   http://wiki.apache.org/incubator/BoardElectionVoteCounting
   http://www.electoral-reform.org.uk/votingsystems/stvi.htm
   http://www.cix.co.uk/~rosenstiel/stvrules/index.htm

for an election with $num open slots.

You have one vote.  Use your vote by entering the label of your
first preference candidate followed by, if desired, the label of your
second preference candidate, and so on until you are indifferent about
the remaining candidates.  The sequence of your preferences is crucial.
You should continue to express preferences only as long as you are able
to place successive candidates in order.  A later preference is considered
only if an earlier preference has a surplus above the quota required for
election, or is excluded because of insufficient support.  Under no
circumstances will a later preference count against an earlier preference.

You may list as many candidates as you wish, but no more than once per
vote (e.g., "xsxp" would be rejected).

$trailer
</pre>
EoSTV
}

sub select_form {
    my ($num, $voter, $issue_content, $trailer) = @_;

    my $html =  <<EoSELECT;

<h1>Cast your vote &lt;$voter&gt;.</h1>
<pre>
$issue_content

= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

To cast your vote, fill in the form entry for your vote below with a
single word single word containing the concatenated labels of the candidates
of your $num choices.  In other words, if you want to vote for the candidates
labeled [x], [s], and [p], then your vote should be "xsp" (order does not
matter).

$trailer
</pre>
EoSELECT
}
