#!/bin/bash
#
# Run a local Pelican build of the site, for dev/test.
#
# REQUIRED ENV VARS:
#
#   BUILDSITE=/path/to/infrastructure-pelican/bin/buildsite.py
#   LIBCMARKDIR=/path/to/cmark-gfm.0.28.3.gfm.12/lib
#
# ### DOCCO on using infra-pel/bin/build-cmark.sh for the lib/
#
# ALSO NEEDED
#   $ pip3 install ezt pelican
#

THIS_SCRIPT=`realpath "$0"`
SITE_DIR=`dirname "$THIS_SCRIPT"`
ROOT_DIR=`dirname "$SITE_DIR"`
#echo $ROOT_DIR

cd "$SITE_DIR"

# export BUILDSITE=~/src/asf/infra-pelican/bin/buildsite.py
# export LIBCMARKDIR=~/src/asf/infra/tools/bintray/cmark-gfm.0.28.3.gfm.12-libs

$BUILDSITE dir --output=/tmp/steve-site.$$ "--yaml-dir=$ROOT_DIR" "--content-dir=$SITE_DIR"
