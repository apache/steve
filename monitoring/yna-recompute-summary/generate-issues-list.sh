#!/bin/sh -e

maildir=${1-/tmp/votem/wd/}
[ -d "$maildir" ] || exit 1

grep -R -h '^Subject:' $maildir \
  | grep -v 'vote on' \
  | perl -lne 'print if s/^Subject: (members\d{6}-\d{8}-)(\S*)/\1\2/' \
  | sort | uniq
