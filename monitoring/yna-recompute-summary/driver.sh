#!/bin/sh -e

maildir=${1-/tmp/votem/wd/}
[ -d "$maildir" ] || exit 1

touch .results.
rm .results.*
sh ./generate-issues-list.sh $maildir | perl ./count.pl $maildir
for i in .results.*; do
  cat < $i | sort | uniq > $i.sorted
  mv $i.sorted $i
done
for i in .results.*; do perl ./display-dups.pl $i < $i; done
