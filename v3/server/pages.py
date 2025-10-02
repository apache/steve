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

###
### NOTE: the voting handlers require login for ASF committers only.
### Obviously, this is not a general purpose solution. Something for
### the future, to figure out how we'd like to do configuration
### authorization for various install scenarios and authn systems.
###

import sys
import pathlib

from easydict import EasyDict as edict
import asfpy.stopwatch
import quart
import asfquart.session
from asfquart.auth import Requirements as R

APP = asfquart.APP

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR / APP.cfg.db

sys.path.insert(0, str(THIS_DIR.parent))
import steve.election
import steve.crypto


async def signin_info():
    "Return EZT template data for the Sign-In, in the upper right."
    s = await asfquart.session.read()
    if s:
        return edict(uid=s['uid'], name=s['fullname'], email=s['email'],)

    # No session.
    return edict(uid=None, name=None, email=None,)


@APP.get('/')
@APP.use_template('templates/home.ezt')
async def home_page():
    result = await signin_info()
    result.title = 'Home'

    return result


@APP.get('/voter')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template('templates/voter.ezt')
async def voter_page():
    with asfpy.stopwatch.Stopwatch():
        # These are lists of EasyDict instances for each Election.
        election = steve.election.Election.open_to_pid(DB_FNAME, 'gstein')
        owned = steve.election.Election.owned_elections(DB_FNAME, 'gstein')

    ### for now
    def new_test_election():
        return edict(
            eid=steve.crypto.create_id(),
            title=f'Title blah:{steve.crypto.create_id()}',
            owner_pid='alice',
            authz=None,
            closed=None,
            open_at=None,
            close_at=None,
            )
    election = [ new_test_election() ]
    owned = [ new_test_election() ]

    result = await signin_info()
    result.title = 'Voting'

    result.election = election
    result.owned = owned

    return result


### NOTE: this is for ASF committers only. Obviously, this is not a
### general purpose solution. Something for the future, to figure out
### how we'd like to do configuration authorization for various install
### scenarios and authn systems.
@APP.get('/admin')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template('templates/admin.ezt')
async def admin_page():
    result = await signin_info()
    result.title = 'Administration'

    return result


@APP.get('/profile')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template('templates/profile.ezt')
async def profile_page():
    result = await signin_info()
    result.title = 'Profile'

    return result


@APP.get('/settings')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template('templates/settings.ezt')
async def settings_page():
    result = await signin_info()
    result.title = 'Settings'

    return result


@APP.get('/privacy')
@APP.use_template('templates/privacy.ezt')
async def privacy_page():
    result = await signin_info()
    result.title = 'Privacy'

    return result


@APP.get('/about')
@APP.use_template('templates/about.ezt')
async def about_page():
    result = await signin_info()
    result.title = 'About'

    return result


# Route to serve static files (CSS and JS)
@APP.route('/static/<path:filename>')
async def serve_static(filename):
    return await quart.send_from_directory('static', filename)
