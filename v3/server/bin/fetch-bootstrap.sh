#!/usr/bin/env bash

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# Fetch latest bootstrap, and places files into our git working copy.

#set -x

VERSION="5.3.1"
DIST="bootstrap-${VERSION}-dist"
B_URL="https://github.com/twbs/bootstrap/releases/download/v${VERSION}/${DIST}.zip"

I_VERSION="1.13.1"
I_DIST="bootstrap-icons-${I_VERSION}"
I_URL="https://github.com/twbs/icons/releases/download/v${I_VERSION}/${I_DIST}.zip"

S_VERSION="1.15.0"
S_DIST="Sortable-${S_VERSION}"
S_URL="https://github.com/SortableJS/Sortable/releases/download/${S_VERSION}/${S_DIST}.zip"

THIS_DIR=$(dirname "`realpath $0`")
PARENT_DIR=$(dirname "$THIS_DIR")
STATIC_DIR="${PARENT_DIR}/static"

# --------------------
#
# Grab the Bootstrap package (CSS and JS)
#

ZIPFILE="${THIS_DIR}/bs.zip"

echo "Fetching: ${B_URL}"
curl -q --location "${B_URL}" --output "${ZIPFILE}"

echo "Extracting: bootstrap.min.css"
unzip -joq "${ZIPFILE}" "${DIST}/css/bootstrap.min.css" -d "${STATIC_DIR}/css"
echo "Extracting: bootstrap.min.css.map"
unzip -joq "${ZIPFILE}" "${DIST}/css/bootstrap.min.css.map" -d "${STATIC_DIR}/css"
echo "Extracting: bootstrap.bundle.min.js"
unzip -joq "${ZIPFILE}" "${DIST}/js/bootstrap.bundle.min.js" -d "${STATIC_DIR}/js"
echo "Extracting: bootstrap.bundle.min.js.map"
unzip -joq "${ZIPFILE}" "${DIST}/js/bootstrap.bundle.min.js.map" -d "${STATIC_DIR}/js"

echo ""
echo "Modify templates with new integrity values:"
echo "bootstrap.min.css:"
echo -n "sha384-" ; openssl dgst -sha384 -binary "${STATIC_DIR}/css/bootstrap.min.css" | openssl base64 -A ; echo ""
echo "bootstrap.bundle.min.js:"
echo -n "sha384-" ; openssl dgst -sha384 -binary "${STATIC_DIR}/js/bootstrap.bundle.min.js" | openssl base64 -A ; echo ""
echo ""

# --------------------
#
# Grab the Bootstrap icons package.
#
I_ZIPFILE="${THIS_DIR}/icons.zip"

echo "Fetching: ${I_URL}"
curl -q --location "${I_URL}" --output "${I_ZIPFILE}"

echo "Extracting: bootstrap-icons.css"
unzip -joq "${I_ZIPFILE}" "${I_DIST}/bootstrap-icons.css" -d "${STATIC_DIR}/css"

echo "Extracting: fonts/bootstrap-icons.woff2"
unzip -joq "${I_ZIPFILE}" "${I_DIST}/fonts/bootstrap-icons.woff2" -d "${STATIC_DIR}/css/fonts"
echo "Extracting: fonts/bootstrap-icons.woff"
unzip -joq "${I_ZIPFILE}" "${I_DIST}/fonts/bootstrap-icons.woff" -d "${STATIC_DIR}/css/fonts"

# --------------------
#
# Grab the SortableJS package (JS)
#

S_ZIPFILE="${THIS_DIR}/sortable.zip"

echo "Fetching: ${S_URL}"
curl -q --location "${S_URL}" --output "${S_ZIPFILE}"

echo "Extracting: Sortable.min.js"
unzip -joq "${S_ZIPFILE}" "${S_DIST}/Sortable.min.js" -d "${STATIC_DIR}/js"

echo ""
echo "Modify templates with new integrity values:"
echo "Sortable.min.js:"
echo -n "sha384-" ; openssl dgst -sha384 -binary "${STATIC_DIR}/js/Sortable.min.js" | openssl base64 -A ; echo ""
echo ""

# --------------------

echo ""
echo "NOTE: zip files can now be removed:"
echo "  ${ZIPFILE}"
echo "  ${I_ZIPFILE}"
echo "  ${S_ZIPFILE}"
