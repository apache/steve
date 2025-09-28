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
import pathlib

from easydict import EasyDict as edict
import asfpy.stopwatch
import quart
import asfquart
from asfquart.auth import Requirements as R

APP = asfquart.APP

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR / APP.cfg.db

sys.path.insert(0, str(THIS_DIR.parent))
import steve.election


@APP.get('/')
@APP.use_template('templates/home.ezt')
async def home_page():
    return {
        'title': 'Home',
    }


@APP.get('/voter')
@asfquart.auth.require({R.committer})
@APP.use_template('templates/voter.ezt')
async def voter_page():
    with asfpy.stopwatch.Stopwatch():
        election = steve.election.Election.open_to_pid(DB_FNAME, 'gstein')
        owned = steve.election.Election.owned_elections(DB_FNAME, 'gstein')

    election = [ edict(eid='123', title='test election') ]
    owned = [ edict(eid='456', title='another', authz=None, closed=None) ]

    return {
        'title': 'Voting',
        'election': election,
        'owned': owned,
    }


@APP.get('/admin')
@asfquart.auth.require({R.committer})
@APP.use_template('templates/admin.ezt')
async def admin_page():
    return {
        'title': 'Administration',
    }


@APP.get('/profile')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template('templates/profile.ezt')
async def profile_page():
    return {
        'title': 'Profile',
    }


@APP.get('/settings')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template('templates/settings.ezt')
async def settings_page():
    return {
        'title': 'Settings',
    }


@APP.get('/sign-out')
@asfquart.auth.require  # Bare decorator means just require a valid session
async def sign_out():
    ### clear the cookie?
    return '', 204


@APP.get('/privacy')
@APP.use_template('templates/privacy.ezt')
async def privacy_page():
    return {
        'title': 'Privacy',
    }


@APP.get('/about')
@APP.use_template('templates/about.ezt')
async def about_page():
    return {
        'title': 'About',
    }


# Route to serve static files (CSS and JS)
@APP.route('/static/<path:filename>')
async def serve_static(filename):
    return await quart.send_from_directory('static', filename)
