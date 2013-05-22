#!/bin/sh
#####
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#####
PREFIX=/usr/local/apache2-install/people.apache.org/current
CFG=/home/voter/www/conf/httpd.conf

case "$1" in
    start)
        [ -x ${PREFIX}/bin/httpd ] && ${PREFIX}/bin/httpd -f ${CFG} -k start > /dev/null && echo -n ' apache'
        ;;
    stop)
        [ -r /var/run/httpd-vote.apache.org.pid ] && ${PREFIX}/bin/httpd -f ${CFG} -k stop > /dev/null && echo -n ' apache'
        ;;
    *)
        echo "Usage: `basename $0` {start|stop}" >&2
        ;;
esac

exit 0
