#!/usr/bin/env -S uv run --script

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
# /// script
# dependencies = [
#    "asfpy>=0.56",
#    "asfquart>=0.1.12",
#    "ezt>=1.1",
#    "easydict>=1.13",
#    "cryptography>=46.0.5,<47",
#    "argon2-cffi>=25.1.0,<26",
# ]
# ///

import sys
import logging
import pathlib

_LOGGER = logging.getLogger(__name__)
DATE_FORMAT = '%m/%d %H:%M'

THIS_DIR = pathlib.Path(__file__).resolve().parent
CERTS_DIR = THIS_DIR / 'certs'


def create_app():
    "Create the asfquart app and its endpoints."

    ### is this really needed right now?
    # Avoid OIDC
    import asfquart.generics

    asfquart.generics.OAUTH_URL_INIT = (
        'https://oauth.apache.org/auth?state=%s&redirect_uri=%s'
    )
    asfquart.generics.OAUTH_URL_CALLBACK = 'https://oauth.apache.org/token?code=%s'

    app = asfquart.construct('steve', app_dir=THIS_DIR, static_folder=None)

    # Now that we have an APP, import modules that will add page
    # and API endpoints into the APP.
    import pages  # noqa: F401
    import api  # noqa: F401

    return app  # also available as asfquart.APP now


def run_standalone():
    "Run as a standalone server."

    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='[{asctime}|{levelname}|{name}] {message}',
        datefmt=DATE_FORMAT,
    )

    # Switch some loggers to INFO, rather than DEBUG
    logging.getLogger('selector_events').setLevel(logging.INFO)
    logging.getLogger('hpack').setLevel(logging.INFO)
    logging.getLogger('sslproto').setLevel(logging.INFO)
    ### above is good, but leaks stuff. This quiets things. too much?
    ### other way to approach: what in asyncio do we need to observe?
    logging.getLogger('asyncio').setLevel(logging.INFO)

    _LOGGER.info(' ** Run-mode: Standalone')

    # Set up the STeVe app, then we'll start it up.
    app = create_app()

    # Note: "pages" imports "steve.election". Pull that package into
    # our local namespace.
    steve = sys.modules['steve']

    # There are other things to watch, and cause a reload.
    extra_files = {
        steve.election.QUERIES,
    }

    kwargs = {}
    if app.cfg.server.certfile:
        kwargs['certfile'] = CERTS_DIR / app.cfg.server.certfile
        kwargs['keyfile'] = CERTS_DIR / app.cfg.server.keyfile
        extra_files.update((kwargs['certfile'], kwargs['keyfile']))

    # Spool up the app!
    app.runx(port=app.cfg.server.port, extra_files=extra_files, **kwargs)

    # print('LOGGERS:', sorted(_LOGGER.manager.loggerDict.keys()))
    # print(_LOGGER.manager.loggerDict['sslproto'])


def run_asgi():
    "Run as an ASGI process; eg. Hypercorn"

    # NOTE: no-op if Hypercorn has set up the root logger.
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='[{asctime}|{levelname}|{name}] {message}',
        datefmt=DATE_FORMAT,
    )

    # Make some loggers explicitly INFO, rather than default to DEBUG.
    logging.getLogger('watchfiles.main').setLevel(logging.INFO)

    # Configure our app's loggers (rather than root logger default).
    _LOGGER.setLevel(logging.DEBUG)

    # Okay. Time to be a Hypercorn-based ASGI app.

    _LOGGER.info(' ** Run-mode: ASGI')

    global steve_app
    steve_app = create_app()


if __name__ == '__main__':
    # $ ./main.py
    run_standalone()
else:
    # Using Hypercorn:
    #
    #   $ uv run python -m hypercorn main:steve_app
    #
    # NOTE: without our extended shutdown_trigger, we cannot reload
    # or restart on .py changes, extra_files changes, or respond to
    # SIGUSR2 to restart. Hypercorn will respond to SIGTERM/SIGINT
    # and shutdown.
    run_asgi()
