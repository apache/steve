import os, sys, random, time

path = os.path.abspath(os.getcwd() + "/..")
sys.path.append(path)

version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
    
config = configparser.RawConfigParser()
config.read('../steve.cfg')

homedir = config.get("general", "homedir")

from lib import election, voter, constants
import argparse

parser = argparse.ArgumentParser(description='Command line options.')
parser.add_argument('--id', dest='id', type=str, nargs=1,
                   help='Election ID: If defined, attempt to create an election using this as the election ID (OPTIONAL)')
parser.add_argument('--owner', required=True, dest='owner', nargs=1,
                   help='Sets the owner of this election, as according to steve.cfg [REQUIRED]')
parser.add_argument('--title', required=True, dest='title', nargs=1,
                   help='Sets the title (name) of the election [REQUIRED]')
parser.add_argument('--monitors', dest='monitors', nargs=1,
                   help='Comma-separated list of email addresses to use for monitoring (OPTIONAL)')
parser.add_argument('--public', dest='public', action='store_true',
                   help='If set, create the election as a public (open) election where anyone can vote (OPTIONAL)')

args = parser.parse_args()
eid = args.id
if not eid:
    eid = ("%08x" % int(time.time() * random.randint(1,999999999999)))[0:8]
print("Creating new election with ID %s" % eid)
monitors = []
if args.monitors:
    monitors = args.monitors.split(",")
election.createElection(eid, args.title, args.owner, monitors, 0, 0, args.public)

print("Election created!")
print("Election ID: %s" % eid)
print("Election Admin URL: %s/edit_election.html?%s" % (config.get("general", "rooturl"), eid))
