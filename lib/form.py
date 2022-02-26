#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os, sys
import cgi

ctype, pdict = cgi.parse_header(os.environ['CONTENT_TYPE'] if 'CONTENT_TYPE' in os.environ else "")
if ctype == 'multipart/form-data':
    xform = cgi.parse_multipart(sys.stdin, pdict)
else:
    xform = cgi.FieldStorage();


def getvalue(key):
    try:
        val = str("".join(xform.get(key, "")))
        if val == "":
            val = None
    except:
        val = xform.getvalue(key)
    if val:
        return val.replace("<", "&lt;")
    else:
        return None
