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
""" Buggy standalone server for testing out pySTeVe """

portno = 8080


import BaseHTTPServer
import CGIHTTPServer
from SocketServer import ThreadingMixIn
import cgitb
import base64
import os
import sys, traceback

cgitb.enable()
server = BaseHTTPServer.HTTPServer

handler = CGIHTTPServer.CGIHTTPRequestHandler
server_address = ("", portno)
handler.cgi_directories = ["/www/cgi-bin"]
handler.cgi_info = {}

path = os.path.abspath(os.getcwd())


# EDIT THIS OR SOME SUCH!!!!
karma = {
    'admin': 'demo'
}

def doTraceBack():
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
    traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)
    traceback.print_exc()
    
 
class pysteveHTTPHandler(handler):
    
    cgi_directories = ["/www/cgi-bin"]
    
    def do_AUTHHEAD(self):
        print "send header"
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm=\"STeVe Administration\"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        
    def do_GET(self):
        try:
            print(self.path)
            if self.path.startswith("/steve/admin"):
                if self.headers.getheader('Authorization') == None:
                    self.do_AUTHHEAD()
                    self.wfile.write('no auth header received')
                    return
                else:
                    authed = False
                    auth = self.headers.getheader('Authorization')[6:]
                    arr = base64.decodestring(auth).split(":", 2)
                    if len(arr) == 2:
                        name = arr[0]
                        password= arr[1]
                        if karma.get(name) and karma[name] == password:
                            authed = True
                    if not authed:
                        self.do_AUTHHEAD()
                        self.wfile.write('Wrong user or pass received')
                        return
                path_info = self.path.replace("/steve/admin", "", 1)
                os.chdir(path + "/www/cgi-bin")
                self.cgi_info = ("/", "rest_admin.py" + path_info)
                self.run_cgi()
                return
            elif self.path.startswith("/steve/voter"):
                path_info = self.path.replace("/steve/voter", "", 1)
                os.chdir(path + "/www/cgi-bin")
                self.cgi_info = ("/", "rest_voter.py" + path_info)
                self.run_cgi()
                return
            else:
                os.chdir(path)
                self.path = "/www/htdocs" + self.path
            print(self.path)
            handler.do_GET(self)
            
        except Exception as err:
            doTraceBack()
       
    def do_POST(self):
        self.do_GET() #Same diff, eh...
        
class ThreadedHTTPServer(ThreadingMixIn, server):
    """Moomins live here"""
    

if __name__ == '__main__':
    server = ThreadedHTTPServer(('', portno), pysteveHTTPHandler)
    print("Running at http://youriphere:%u/ ..." % portno)
    server.serve_forever()