#!/usr/bin/env python
# ============================================================
#
# nstv-rank.py:
#   Usage: nstv-rank.py [-h] [-b] [-o filename] inputfile(s)
#    -h: Usage info (help)
#    -b: Generate BLT STV data format file
#    -o <filename> : Output file (default stdout)
#
# This script is designed to accept as input data in
# the form as returned from the ASF Voter Tool 'Final
# Tally' report email and generate output in the format
# to be used by various STV ballot-counting software.
#
# The script allows you to use as input the full Email
# message of the final tally; it takes care of correctly
# handling duplicate votes (accepting only the last one)
# as well as non-vote lines. Vote lines MUST have the
# following format:
#
# [2006/06/13 18:22:30] 0422f389874d7a8ecfd2fabea0a152ed lagd
# [2006/06/13 18:23:15] 9c58d57506a17c83b9d4cc8c0ed4a31e lgej
# [2006/06/13 18:28:27] 9db55691a072f88d79968eed8297dc90 fcaki
# [2006/06/13 19:01:13] a6d1332887e40af1dd2405cd2abf1e77 glfj
# [2006/06/13 19:22:45] a9472aa4f7df905173acd8fe2d8edcb2 jkc
# [2006/06/13 20:42:33] adc9914bb9112d8da4cddd6353e09ef1 eagk
#
# NOTE: All this depends on the format of the Final Tally
# Email not changing. The assumptions are that the vote
# list is ALWAYS in correct chronological order, with newer
# votes after older ones.
#
# By default, it prints out a file in the format expected by
# Voting Systems Toolbox (http://sourceforge.net/projects/votesystem):
#
# 32d4a49fbe6f1ee8a4f6a47f45fd5bbf,g,c,j,e,k,i,f,d,h
# 04e53da3b92cd9a36fd2e9eba91915f8,i,c,j,e,l,a,g,d,b
# 5e3bea51a6eef2d09722069f0c6178a5,a,c,j,g,l,h
# f58528624ce66abe6ee8039e5d6a40f0,c,e,h,j,i,g,b,d,f,a,k,l
#
# It can also print out a file in BLT format, via the '-b' argument.
##
#### VoteMain instructions ####
# After installing Voting Systems Toolbox, you can execute the 'VoteMain'
# program as
#
#   java -cp Vote-0-4.jar VoteMain -system stv-meek -seats 9 outputFile
#
# where outputFile is the result of this script (rank).
#
# The output of  'VoteMain' program is the result of the elections.
#
# Note that the 'VoteMain' program can detect duplicate votes, as well as votes
# with incorrect labels.
##
#### OpenSTV instructions ####
# OpenSTV (http://stv.sourceforge.net/) is a newer and better
# maintained STV counting codebase. It requires the use of BLT
# input files.
#
# The ASF uses Meek STV with:
#   Precision: 6
#   Threshold:  Droop | Dynamic | Fractional
#

import getopt
import os.path
import sys
import re
import string
import ConfigParser

def read_nominees(votefile):
  ini_fname = os.path.join(os.path.dirname(votefile),
                           'board_nominations.ini')

  config = ConfigParser.ConfigParser()
  config.read(ini_fname)
  try:
    return dict(config.items('nominees'))
  except:
    print >> sys.stderr, "Error processing input file: " + ini_fname
    print >> sys.stderr, " Goodbye!"
    sys.exit(2)

def usage(error=None):
    print >> sys.stderr, "nstv-rank.py:"
    print >> sys.stderr, " Usage: nstv-rank.py [-h] [-b] [-o filename] inputfile(s)"
    print >> sys.stderr, "   -h: This info"
    print >> sys.stderr, "   -b: Generate BLT STV data format file"
    print >> sys.stderr, "   -o <filename> : Output file (default stdout)"
    if error:
        print >> sys.stderr, "Error: " + error

def read_votes(args):
    votes = { }
    vote_pat = re.compile(r'\[.{19}\]\s+([\w\d]{32})\s+([a-z]{1,26})', re.I)
    for fname in args:
        try:
            for line in open(fname):
                line = string.strip(line)
                vote = vote_pat.search(line)
                if vote:
                    votes[vote.group(1)] = vote.group(2)
        except:
            print >> sys.stderr, "Error processing input file: " + fname
            print >> sys.stderr, " Goodbye!"
            sys.exit(2)
    return votes

def print_tally(args, output, blt):
    votes = read_votes(args)
    nominees = read_nominees(args[0])
    nomkeys = sorted(nominees)
    numseats = 9

    if output:
        try:
            sys.stdout = open(a, 'w')
        except:
            print >> sys.stderr, "Cannot open output file: " + a
            print >> sys.stderr, " Goodbye!"
            sys.exit(2)

    if blt:
        numcands = len(nomkeys)
        print "%d %d" % (numcands, numseats)
        for id in votes.keys():
            line = [ ]
            for vote in votes[id]:
                value = ord(vote) - ord('a') + 1
                line.append(str(value))
            line = "1 "+ " ".join(line) + " 0"
            print line
        print "0"
        for id in nomkeys:
            print '"%s"' % nominees[id]
        print '"ASF STV Board Election"'
  
    else:
        print "rank order"
        line = [ ]
        for id in nomkeys:
            line.append("%20.20s" % nominees[id])
        line = "NAME, " + ", ".join(line)
        print line
        line = [ ]
        for id in nomkeys:
            line.append("%20.20s" % id)
        line = "LABEL," + ", ".join(line)
        print line
        for id in votes.keys():
            line = id + "," + ",".join(votes[id])
            print line

    
if __name__ == '__main__':

    try:
        opts, args = getopt.getopt(sys.argv[1:], "ho:b")
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)
    output = None
    blt = False
    for o, a in opts:
        if o == "-b":
            blt = True
        elif o == "-h":
            usage()
            sys.exit()
        elif o == "-o":
            output = a
    if len(args) > 0:
        print_tally(args, output, blt)
    else:
        usage("No input file")
        sys.exit(2)
