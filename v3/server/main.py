#!/usr/bin/env python3
#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import sys
import logging
import pathlib

_LOGGER = logging.getLogger(__name__)
DATE_FORMAT = '%m/%d %H:%M'

THIS_DIR = pathlib.Path(__file__).resolve().parent
CERTS_DIR = THIS_DIR / 'certs'


def main():
    logging.basicConfig(level=logging.DEBUG,
                        style='{',
                        format='[{asctime}|{levelname}|{module}] {message}',
                        datefmt=DATE_FORMAT,
                        )

    # Switch some loggers to INFO, rather than DEBUG
    logging.getLogger('selector_events').setLevel(logging.INFO)
    logging.getLogger('hpack').setLevel(logging.INFO)
    logging.getLogger('sslproto').setLevel(logging.INFO)

    ### is this really needed right now?
    # Avoid OIDC
    import asfquart.generics
    asfquart.generics.OAUTH_URL_INIT = "https://oauth.apache.org/auth?state=%s&redirect_uri=%s"
    asfquart.generics.OAUTH_URL_CALLBACK = "https://oauth.apache.org/token?code=%s"

    app = asfquart.construct('steve')

    # Now that we have an APP, import modules that will add page
    # and API endpoints into the APP.
    import pages  # pylint: disable=unused-import
    import api  # pylint: disable=unused-import

    # Note: "pages" imports "steve.election". Pull that package into
    # our local namespace.
    steve = sys.modules['steve']

    # There are other things to watch, and cause a reload.
    extra_files = {
        steve.election.QUERIES,
        }

    kwargs = { }
    if app.cfg.server.certfile:
        kwargs['certfile'] = CERTS_DIR / app.cfg.server.certfile
        kwargs['keyfile'] = CERTS_DIR / app.cfg.server.keyfile
        extra_files.update((kwargs['certfile'], kwargs['keyfile']))

    # Spool up the app!
    app.runx(port=app.cfg.server.port,
             extra_files=extra_files,
             **kwargs)

    #print('LOGGERS:', sorted(_LOGGER.manager.loggerDict.keys()))
    #print(_LOGGER.manager.loggerDict['sslproto'])


if __name__ == '__main__':
    main()
