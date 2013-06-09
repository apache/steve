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
import hashlib

from asf.utils.emails import canonical_email_address

def get_hash_of(datum):
    "Compute the (hex) MD5 hash of the string DATUM."
    return hashlib.md5(datum).hexdigest()


def hash_file(fname):
    "Compute the (hex) MD5 hash of the file FNAME."
    return get_hash_of(open(fname).read())

def get_group(fname):
    "Return the group of voters, as a list of email addresses."

    group = []
    for line in open(fname).readlines():
        i = line.find('#')
        if i >= 0:
            line = line[:i]
        line = line.strip()
        if not line:
            continue
        if '@' not in line:
            raise ValueError('%s: voter must be an Internet e-mail address.' % (line,))
        group.append(canonical_email_address(line))

    return group
