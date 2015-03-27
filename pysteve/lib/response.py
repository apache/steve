#!/usr/bin/env python
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
import json

responseCodes = {
    200: 'Okay',
    201: 'Created',
    206: 'Partial content',
    304: 'Not Modified',
    400: 'Bad Request',
    403: 'Access denied',
    404: 'Not Found',
    410: 'Gone',
    500: 'Server Error'
}

def respond(code, js):
    c = responseCodes[code] if code in responseCodes else "Unknown Response Code(?)"
    out = json.dumps(js, indent=4)
    print("Status: %u %s\r\nContent-Type: application/json\r\nCache-Control: no-cache\r\nContent-Length: %u\r\n" % (code, c, len(out)))
    print(out)
    
    
    