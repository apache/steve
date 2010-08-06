#!/usr/bin/python
#
# Take a voter outputFile, and either strip all but the specified candidates,
# or remove the specified candidates.

import sys,re,string

if len(sys.argv) == 1:
  sys.stderr.write("usage: %s [-]names... <inputFile >outputFile\n" %
    sys.argv[0])
  exit(1)

# read header
header = sys.stdin.readline()
names  = re.split(',\s+', sys.stdin.readline().strip())
labels = re.split(',\s+', sys.stdin.readline().strip())

# validate input
valid = map(string.lower, names[1:] + labels[1:])
selection = map(string.lower, sys.argv[1:])
for arg in selection:
  if arg.lstrip('-') not in valid:
    sys.stderr.write('invalid selection: %s\n' % arg)
    exit(1)

# filter candidates
if selection[0][0] == '-':
  for i in range(len(labels)-1,0,-1):
    if '-'+names[i].lower() in selection or '-'+labels[i] in selection:
      names.pop(i)
      labels.pop(i)
else:
  for i in range(len(labels)-1,0,-1):
    if names[i].lower() not in selection and labels[i] not in selection:
      names.pop(i)
      labels.pop(i)

# output modified header
print header,
print ', '.join(names)
print ', '.join(labels)

# filter votes
read = written = 0
for vote in sys.stdin:
  read += 1
  votes = vote.strip().split(',')
  for i in range(len(votes)-1,0,-1):
    if votes[i] not in labels:
      votes.pop(i)
  if len(votes)>1:
    written += 1
    print ','.join(votes)

sys.stderr.write("%d votes read\n%d votes written\n" % (read, written))
