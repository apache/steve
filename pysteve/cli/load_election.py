#!/usr/bin/env python3
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

#
# Load/create an election with a set of issues specified in a .yaml file
#
### NOTE:
# relies on using .netrc for user/pass. Cuz not gonna bother doing better.
#

import sys
import os
import logging

import yaml  # pip install PyYAML
import requests  # pip install requests
import easydict

LOGGER = logging.getLogger(__name__)


def main(y_fname):
    cfg = easydict.EasyDict(yaml.safe_load(open(y_fname)))

    election = cfg.election
    LOGGER.info(f'ELECTION: {election.eid}')
    ensure_election(cfg)

    ### list current issues
    ### remove all issues
    ### load issues from the YAML


def ensure_election(cfg):
    s = requests.Session()

    eid = cfg.election.eid
    r = s.get(f'{cfg.config.endpoint}/view/{eid}')
    LOGGER.debug(f'HEADERS: {r.request.headers}')
    if r.status_code == 200:
        # All good. The election has already been created.
        return  ### return the content? update to ensure it matches?
    if r.status_code != 404:
        # Something is wrong.
        LOGGER.error(f'UNKNOWN: {r.status_code}')
        LOGGER.debug(f'BODY: {r.text}')
        raise Exception

    # Got a 404 saying the election doesn't exist. So create it.
    payload = {
        'title': cfg.election.title,
        'owner': cfg.config.user,
        'monitors': ','.join(cfg.election.monitors),

        ### Below are optional. Skip for now.
        #'starts': d,
        #'ends': e,
        #'open': f
        }

    ### use a PreparedRequest so we can debug the URL used
    url = f'{cfg.config.endpoint}/setup/{eid}'
    #req = requests.Request('POST', url, data=payload)
    #prepped = req.prepare()
    #LOGGER.debug(f'HEADERS: {prepped.headers}')

    r = s.post(url, data=payload)
    LOGGER.debug(f'HEADERS: {r.request.headers}')
    if r.status_code != 201:
        # Something is wrong.
        LOGGER.error(f'UNKNOWN: {r.status_code}')
        LOGGER.debug(f'BODY: {r.text}')
        raise Exception

    LOGGER.debug(r.json())


if __name__ == '__main__':
    ### TODO: fancy arg parsing
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1])
