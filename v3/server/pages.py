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
import datetime

from easydict import EasyDict as edict
import asfpy.stopwatch
import quart
import asfquart.session
from asfquart.auth import Requirements as R
import ezt

APP = asfquart.APP

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR / APP.cfg.db
TEMPLATES = THIS_DIR / 'templates'

sys.path.insert(0, str(THIS_DIR.parent))
import steve.election
import steve.crypto

# Formatted values to inject into templates.
FMT_DATE = '%b %d'
FMT_DATE_FULL = '%Y-%m-%d %H:%M'
SOON_1HOUR = 60 * 60
SOON_CUTOFF = 48 * SOON_1HOUR  # 48 hours, in seconds

T_BAD_EID = APP.load_template(TEMPLATES / 'e_bad_eid.ezt')


async def signin_info():
    "Return EZT template data for the Sign-In, in the upper right."
    s = await asfquart.session.read()
    if s:
        return edict(uid=s['uid'], name=s['fullname'], email=s['email'],)

    # No session.
    return edict(uid=None, name=None, email=None,)


@APP.get('/')
@APP.use_template(TEMPLATES / 'home.ezt')
async def home_page():
    result = await signin_info()
    result.title = 'Home'

    return result


@APP.get('/voter')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template(TEMPLATES / 'voter.ezt')
async def voter_page():
    result = await signin_info()
    result.title = 'Voting'

    with asfpy.stopwatch.Stopwatch():
        # These are lists of EasyDict instances for each Election.
        election = steve.election.Election.open_to_pid(DB_FNAME, result.uid)
        owned = steve.election.Election.owned_elections(DB_FNAME, result.uid)

    result.election = [ postprocess_election(e) for e in election ]

    result.len_election = len(election)
    result.len_owned = len(owned)

    return result


@APP.get('/vote-on/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template(TEMPLATES / 'vote-on.ezt')
async def vote_on_page(eid):
    result = await signin_info()
    result.title = 'Vote On Election'

    e = steve.election.Election(DB_FNAME, eid)

    try:
        md = e.get_metadata()
    except AttributeError:
        # If the EID is wrong, the fetch fails trying to access metadata.
        ### YES, very poor way to signal a bad EID. fix this.
        result.title = 'Unknown Election'
        result.eid = eid
        # Note: result.uid (and friends) are needed for the navbar.
        raise_404(T_BAD_EID, result)
        # NOTREACHED

    ### check authz

    ### rando for now. fetch the issues, and put in a count.
    result.issue_count = 7

    return result


@APP.get('/admin')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template(TEMPLATES / 'admin.ezt')
async def admin_page():
    result = await signin_info()
    result.title = 'Administration'

    with asfpy.stopwatch.Stopwatch():
        # These are lists of EasyDict instances for each Election.
        election = steve.election.Election.open_to_pid(DB_FNAME, result.uid)
        owned = steve.election.Election.owned_elections(DB_FNAME, result.uid)

    ### for now. future: adjust query
    for e in owned:
        e.issue_count = 5
        e.owner_pid = result.uid

    result.owned = [ postprocess_election(e) for e in owned ]

    result.len_election = len(election)
    result.len_owned = len(owned)

    return result


@APP.get('/profile')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template(TEMPLATES / 'profile.ezt')
async def profile_page():
    result = await signin_info()
    result.title = 'Profile'

    return result


@APP.get('/settings')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template(TEMPLATES / 'settings.ezt')
async def settings_page():
    result = await signin_info()
    result.title = 'Settings'

    return result


@APP.get('/privacy')
@APP.use_template(TEMPLATES / 'privacy.ezt')
async def privacy_page():
    result = await signin_info()
    result.title = 'Privacy'

    return result


@APP.get('/about')
@APP.use_template(TEMPLATES / 'about.ezt')
async def about_page():
    result = await signin_info()
    result.title = 'About'

    return result


# Route to serve static files (CSS and JS)
@APP.route('/static/<path:filename>')
async def serve_static(filename):
    return await quart.send_from_directory('static', filename)


def format_datetime(dt):
    "Format a datetime as absolute or relative."

    # Carry through an absent datetime.
    if not dt:
        return None

    delta = dt.timestamp() - datetime.datetime.now().timestamp()
    if 0 < delta < SOON_CUTOFF:
        if delta < SOON_1HOUR:
            return f'in about {int(delta / 60)} minutes'
        return f'in about {int(delta / 60 / 60)} hours'

    return f'on {dt.strftime(FMT_DATE)}'  # short format


def postprocess_election(e):
    "Post-process attributes in an Election, as an EasyDict."

    # Anything but 1 means the Election is not closed.
    e.closed = ezt.boolean(e.closed == 1)

    # Anything but 1 means the Election is not open.
    e.is_opened = ezt.boolean(e.is_opened == 1)

    # note: an election has an Edit state: not open, not closed.

    # Format dates, if present.
    dt_open = e.open_at and datetime.datetime.fromtimestamp(e.open_at)
    e.fmt_open_at = format_datetime(dt_open)
    e.fmt_open_at_full = dt_open and dt_open.strftime(FMT_DATE_FULL)
    dt_close = e.close_at and datetime.datetime.fromtimestamp(e.close_at)
    e.fmt_close_at = format_datetime(dt_close)
    e.fmt_close_at_full = dt_close and dt_close.strftime(FMT_DATE_FULL)

    return e


def raise_404(template, data):
    content = asfquart.utils.render(template, data)
    quart.abort(quart.Response(content, status=404, mimetype='text/html'))
