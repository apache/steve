import os, sys, random, time

path = os.path.abspath(os.getcwd() + "/..")
sys.path.append(path)

version = 2
if sys.hexversion < 0x03000000:
    import ConfigParser as configparser
else:
    import configparser
    version = 3
    
print("Reading steve.cfg")
config = configparser.RawConfigParser()
config.read('../steve.cfg')

homedir = config.get("general", "homedir")

from lib import election, voter, constants

print("Attempting to set up STeVe directories...")

if os.path.isdir(homedir):
    print("Creating election folder")
    if os.path.exists(homedir + "/issues"):
        print("Election folder already exists, nothing to do here..")
        sys.exit(-1)
    else:
        try:
            os.mkdir(homedir + "/issues")
            print("All done!")
        except Exception as err:
            print("Could not create dir: %s" % err)
else:
    print("Home dir (%s) does not exist, please create it!" % homedir)
    sys.exit(-1)