#!/usr/bin/perl
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
# steve.pm
# shared functions for Apache Steve.
#

##use strict;

$ECHO     = '/bin/echo';
$CAT      = '/bin/cat';
$MD5      = '/sbin/md5';
$OPENSSL  = '/usr/bin/openssl';
$TOUCH    = '/usr/bin/touch';
$SENDMAIL = '/usr/sbin/sendmail';
$DIFF     = '/usr/bin/diff';
$MV       = '/bin/mv';


$homedir  = '/home/voter';
$issuedir = "$homedir/issues";
$host     = 'people.apache.org';

$ENV{'PATH'}    = "$homedir/bin:/usr/bin:/usr/sbin:/bin:/sbin";
$ENV{'LOGNAME'} = 'voter';
$ENV{'GROUP'}   = 'voter';
$ENV{'USER'}    = 'voter';
$ENV{'HOME'}    = '/home/voter';
$ENV{'MAIL'}    = '/var/mail/voter';

# ==========================================================================
sub get_input_line {
    local ($prompt, $quit_able) = @_;
    local ($_);

    do {
        print("Enter ", $prompt, $quit_able ? " (q=quit): " : ": ");
        $_ = <STDIN>;
        chomp;
        exit(0) if ($quit_able && /^q$/i);
    } while (/^$/);

    return $_;
}

# ==========================================================================
sub get_group {
    local ($groupfile) = @_;
    local ($_, @rv);

    open(INFILE, $groupfile) || die "$pname: cannot open $groupfile: $!\n";
    while ($_ = <INFILE>) {
        chomp;
        s/#.*$//;
        s/\s+$//;
        s/^\s+//;
        next if (/^$/);
        die "$pname: voter must be an Internet e-mail address\n"
            unless (/\@/);
        push(@rv, $_);
    }
    close(INFILE);
    return @rv;
}

# ==========================================================================
sub filestuff {
    local ($filename) = @_;
    local ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
           $atime,$mtime,$ctime,$blksize,$blocks);

    ($dev,$ino,$mode,$nlink,$uid,$gid,$rdev,$size,
     $atime,$mtime,$ctime,$blksize,$blocks) = stat($filename);

    return "$ino:$mtime";
}

# ==========================================================================
sub get_hash_of {
    local ($item) = @_;
    local ($rv);

    if (-x $MD5) {
        $rv = `$MD5 -q -s "$item"` || die "$pname: failed md5: $!\n";
    }
    else {
        $rv = `$ECHO "$item" | $OPENSSL md5`
              || die "$pname: failed openssl md5: $!\n";
    }
    chomp($rv);
    return $rv;
}

# ==========================================================================
sub hash_file {
    local ($filename) = @_;
    local ($rv);

    if (-x $MD5) {
        $rv = `$MD5 -q "$filename"` || die "$pname: failed md5: $!\n";
    }
    else {
        $rv = `$CAT "$filename" | $OPENSSL md5`
              || die "$pname: failed openssl md5: $!\n";
    }
    chomp($rv);
    return $rv;
}

# ==========================================================================
sub debug_hash {
    print "==============================================================\n";
    foreach $voter (@voters) {
        print "$hash1{$voter} $hash2{$voter} $voter\n";
    }
    print "==============================================================\n";
}

# ==========================================================================
sub read_tally {
    local ($filename) = @_;
    local ($_, %rv);

    %rv = ();

    open(INFILE, $filename) || die "$pname: cannot open $filename: $!\n";
    while ($_ = <INFILE>) {
        chomp;
        if (/\] (\S+) (\S+)$/o) {
            $rv{$1} = $2;
        }
        else {
            warn "Invalid vote in tally: $_";
        }
    }
    close(INFILE);

    return %rv;
}

# ==========================================================================
sub found_in_group {
    local ($voter, $groupfile) = @_;
    local ($_);

    open(INFILE, $groupfile) || return 0;
    while ($_ = <INFILE>) {
        chomp;
        s/#.*$//;
        s/\s+$//;
        s/^\s+//;
        if ($_ eq $voter) {
            close(INFILE);
            return 1;
        }
    }
    close(INFILE);
    return 0;
}

# ==========================================================================
sub get_date {
    local ($sec, $min, $hour, $mday, $mon, $year) = gmtime(time);

    return sprintf("%04d/%02d/%02d %02d:%02d:%02d", 1900 + $year,
                   $mon+1, $mday, $hour, $min, $sec);
}

# ==========================================================================
sub contains_duplicates {
    local ($str) = @_;
    local (%ctr, $ch);

    foreach $ch (split(//, $str)) {
        $ctr{$ch} = 1;
    }
    return (length($str) != scalar(keys(%ctr)));
}

# ==========================================================================

sub not_valid {
  my (@votes, %valid);
  @votes = split(//, shift(@_));
  for (@_) {
      chomp;
      $valid{$_} = 1;
  }
  for (@votes) {
      return 1 unless $valid{$_} == 1;
  }
  return 0;
}

# randomize the order in which candidates are listed
#
# candidates are identified with a single alphanumeric character surrounded
# by square brackets as the first non-blank on a line.
#
# candidates are to be listed consecutively, one per line.  If this is
# found not to be the case, NO reordering is performed.
sub randomize {
  my (@prolog, @choices, @epilog);

  push @prolog, shift  while @_ && not $_[0]  =~ /^\s*\[[a-z0-9]\]\s/;
  unshift @epilog, pop while @_ && not $_[-1] =~ /^\s*\[[a-z0-9]\]\s/;
  return @prolog, @_, @epilog if grep !/^\s*\[\S\]\s/, @_;
  push @choices, splice(@_, rand @_, 1) while @_;
  return @prolog, @choices, @epilog;
}

# return the ballot identifiers for each candidate in an issue.
#
# candidates are identified with a single alphanumeric character surrounded
# by square brackets as the first non-blank on a line.
#
# candidates are to be listed consecutively, one per line.
#
sub ballots {
  my (@ballots);

  shift  while @_ && not $_[0]  =~ /^\s*\[[a-z0-9]\]\s/;
  for (@_) {
    if (/^\s*\[([a-z0-9])\]\s/) {
      push @ballots, "$1\n";
    } else {
      last;
    }
  }
  return @ballots;
}

1;
