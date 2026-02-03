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

# Script to check pairwise equality of sorted outputs from REFERENCE_DIR and V3_DIR.
# Assumes REFERENCE_DIR and V3_DIR are populated as per populate_v2_stv.sh.
# For each DATE file, sorts both and compares; silent on match, notes mismatch.

REFERENCE_DIR="v2-stv-ref"
V3_DIR="v3-stv"

# Check if directories exist
if [[ ! -d "$REFERENCE_DIR" || ! -d "$V3_DIR" ]]; then
    echo "Error: Directories $REFERENCE_DIR or $V3_DIR do not exist. Run populate_v2_stv.sh first."
    exit 1
fi

# Iterate over files in REFERENCE_DIR (assuming V3_DIR has matching files)
for ref_file in "$REFERENCE_DIR"/*; do
    if [[ -f "$ref_file" ]]; then
        date=$(basename "$ref_file")
        v3_file="$V3_DIR/$date"
        
        if [[ ! -f "$v3_file" ]]; then
            echo "Warning: No matching file for $date in $V3_DIR"
            continue
        fi
        
        # Sort both files and compare
        if ! diff -q <(sort "$ref_file") <(sort "$v3_file") > /dev/null; then
            echo "Mismatch for $date"
        fi
    fi
done
