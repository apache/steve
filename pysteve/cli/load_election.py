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

    s = requests.Session()

    eid = cfg.election.eid
    LOGGER.info(f'ELECTION: {eid}')
    issues = ensure_election(s, cfg)

    # Remove all the issues, so we can load the new/current set.
    for issue in issues:
        iid = issue['id']
        print(f'DELETING: {iid}')
        r = s.get(f'{cfg.config.endpoint}/delete/{eid}/{iid}')
        if r.status_code != 200:
            # Something is wrong.
            LOGGER.error(f'UNKNOWN: {r.status_code}')
            LOGGER.debug(f'BODY: {r.text}')
            raise Exception

    # Load all the defined issues.
    for idx, issue in enumerate(cfg['issues']):
        iid = f'issue-{idx}'
        print(f'CREATING: {iid}: {issue}')

        payload = {
            'title': issue['title'],
            'description': issue['description'],
            'type': issue['type'],
            ### not needed for YNA. fix as needed
            #'candidates': [ ],
            }
        r = s.post(f'{cfg.config.endpoint}/create/{eid}/{iid}',
                   data=payload)
        if r.status_code != 201:
            # Something is wrong.
            LOGGER.error(f'UNKNOWN: {r.status_code}')
            LOGGER.debug(f'BODY: {r.text}')
            raise Exception

        LOGGER.debug(r.json())


def ensure_election(s, cfg):
    eid = cfg.election.eid
    r = s.get(f'{cfg.config.endpoint}/view/{eid}')
    LOGGER.debug(f'HEADERS: {r.request.headers}')
    if r.status_code == 200:
        # The election has already been created, so return its issues.
        j = r.json()
        LOGGER.debug(f'BODY: {j}')
        return j['issues']
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

    # We created a new election. It has no issues.
    return [ ]


if __name__ == '__main__':
    ### TODO: fancy arg parsing
    logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1])
