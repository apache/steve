#!/usr/bin/perl
# ============================================================
# SCRIPT NAME: check
#
# USAGE: check authorizedVotersFile actualVotersFile
#
# Checks whether the elements listed in 'actualVotersFile' are
# contained in authorizedVotersFile
#
# Both files are expected to contain the hash of voters
#

open(AUTH, "$ARGV[0]");

# Have @auth contain the valid voters
@auth = ();
while(<AUTH>) {
  #chop $_;
  push(@auth, $_);
  #print $_;
}

# Now check against the votes

open(VOTES, "$ARGV[1]");

while(<VOTES>) {

  $result = isInAuth($_);
  unless($result) {
    print "Voter [$_] is not in list of valid voters";
  }
}

# ===================================
sub isInAuth() {
  $voter = $_[0];

  foreach $v (@auth) {
    if($voter =~ $v) {
      return 1;
    }
  }
  return 0;
}
# ============================================================

