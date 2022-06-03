#!/bin/bash
#
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
#

#
# Gather "all" known STV voting processing into a reference directory,
# with full debug output. These files can then be used as a comparison
# to future developments on STV tooling, to ensure consistency.
#

if test "$1" = ""; then echo "USAGE: $0 MEETINGS_DIR"; exit 1; fi
MEETINGS_DIR="$1"

REFERENCE_DIR="v2-stv-ref"
mkdir "$REFERENCE_DIR" || /bin/true

V3_DIR="v3-stv"
mkdir "$V3_DIR" || /bin/true

THIS_FILE=`realpath $0`
THIS_DIR=`dirname "$THIS_file"`
#echo $THIS_FILE
STV_TOOL=`realpath "$THIS_DIR/../../monitoring/stv_tool.py"`
echo $STV_TOOL
V3_TOOL="${THIS_DIR}/run_stv.py"

#echo "ls $MEETINGS_DIR/*/raw_board_votes.txt"

for v in `ls $MEETINGS_DIR/*/raw_board_votes.txt`; do
    #echo $v
    DATE=`echo $v | sed -n 's#.*/\([0-9]*\)/.*#\1#p'`
    echo $DATE
    "$STV_TOOL" -v "$v" > "$REFERENCE_DIR/$DATE"

    MTG_DIR=`dirname "$v"`
    #echo $MTG_DIR
    "$V3_TOOL" "${MTG_DIR}" > "${V3_DIR}/$DATE"
done
