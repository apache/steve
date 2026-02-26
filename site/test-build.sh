#!/bin/bash
#
# Run a local Pelican build of the site, for dev/test.
#
# REQUIRED ENV VARS. FIX THESE.
#
# You will need to clone the repo https://github.com/apache/infrastructure-pelican
# for these tools
# Use infrastructure-pelican/bin/build-cmark.sh to build the cmark-gfm
# library.
export BUILDSITE="../../infrastructure-pelican/bin/buildsite.py"
export LIBCMARKDIR="../../infrastructure-pelican/bin/cmark-gfm-0.28.3.gfm.12/lib"

THIS_SCRIPT=`realpath "$0"`
SITE_DIR=`dirname "$THIS_SCRIPT"`
ROOT_DIR=`dirname "$SITE_DIR"`
VENV_DIR="$SITE_DIR/.venv"

# Create and activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install dependencies
pip install ezt pelican PyYAML markdown gfm

cd "$SITE_DIR"

$BUILDSITE dir --output=/tmp/steve-site.$$ "--yaml-dir=$ROOT_DIR" "--content-dir=$SITE_DIR"
