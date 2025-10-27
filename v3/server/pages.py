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
import functools
import logging

from easydict import EasyDict as edict
import asfpy.stopwatch
import quart
import asfquart.session
from asfquart.auth import Requirements as R
import ezt

APP = asfquart.APP
_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR / APP.cfg.db
TEMPLATES = THIS_DIR / 'templates'

sys.path.insert(0, str(THIS_DIR.parent))
import steve.election
import steve.crypto
import steve.persondb

# Formatted values to inject into templates.
FMT_DATE = '%b %d'
FMT_DATE_FULL = '%Y-%m-%d %H:%M'
SOON_1HOUR = 60 * 60
SOON_CUTOFF = 48 * SOON_1HOUR  # 48 hours, in seconds

T_BAD_EID = APP.load_template(TEMPLATES / 'e_bad_eid.ezt')
T_BAD_IID = APP.load_template(TEMPLATES / 'e_bad_iid.ezt')
T_BAD_PID = APP.load_template(TEMPLATES / 'e_bad_pid.ezt')


async def basic_info():
    "Return base-level EZT template data."

    basic = edict()

    # Flashes are stored in the Session. Fetch and turn each flash into
    # EasyDict objects for use by templates.
    # NOTE: .flash() is called with (message, category), but the
    #   .get_flashed_messages() returns tuples of (category, message)
    basic.flashes = [ edict(message=f[1], category=f[0])
                      for f in quart.get_flashed_messages(with_categories=True) ]

    s = await asfquart.session.read()
    if s:
        basic.update(uid=s['uid'], name=s['fullname'], email=s['email'],)
    else:
        # No session.
        basic.update(uid=None, name=None, email=None,)

    ### generate a real token and store in the session
    basic.csrf_token = 'placeholder'

    return basic


# Define a bunch of helpers for recording "flash" messages in the session.
# Each helper function is:
#    async def flash_FOO(message)
# where FOO is one of the eight Bootstrap alert classes. See:
#    https://getbootstrap.com/docs/5.0/components/alerts/#examples
for _cat in ('primary', 'secondary', 'success', 'danger',
             'warning', 'info', 'light', 'dark', ):
    globals()[f'flash_{_cat}'] = functools.partial(quart.flash, category=_cat)
del _cat


@APP.get('/')
@APP.use_template(TEMPLATES / 'home.ezt')
async def home_page():
    result = await basic_info()
    result.title = 'Home'

    return result


@APP.get('/voter')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template(TEMPLATES / 'voter.ezt')
async def voter_page():
    result = await basic_info()
    result.title = 'Voting'

    with asfpy.stopwatch.Stopwatch():
        # These are lists of EasyDict instances for each Election.
        election = steve.election.Election.open_to_pid(DB_FNAME, result.uid)
        owned = steve.election.Election.owned_elections(DB_FNAME, result.uid)

    result.election = [ postprocess_election(e) for e in election ]

    result.len_election = len(election)
    result.len_owned = len(owned)

    return result


def load_election(func):
    "Decorator to load/pass-argument an Election from EID."

    @functools.wraps(func)
    async def loader(eid):

        try:
            e = steve.election.Election(DB_FNAME, eid)
        except steve.election.ElectionNotFound:
            result = await basic_info()
            result.title = 'Unknown Election'
            result.eid = eid
            # Note: result.uid (and friends) are needed for the navbar.
            raise_404(T_BAD_EID, result)
            # NOTREACHED

        _LOGGER.debug(f'Loaded: {e}')

        ### check authz

        return await func(e)

    return loader


def load_election_issue(func):
    "Decorator to load/pass-argument an Election from EID."

    @functools.wraps(func)
    async def loader(eid, iid):

        try:
            e = steve.election.Election(DB_FNAME, eid)
        except steve.election.ElectionNotFound:
            result = await basic_info()
            result.title = 'Unknown Election'
            result.eid = eid
            # Note: result.uid (and friends) are needed for the navbar.
            raise_404(T_BAD_EID, result)
            # NOTREACHED

        _LOGGER.debug(f'Loaded: {e}')

        ### check authz

        try:
            i = e.get_issue(iid)
        except steve.election.IssueNotFound:
            result = await basic_info()
            result.title = 'Unknown Issue'
            result.eid = eid
            result.iid = iid
            # Note: result.uid (and friends) are needed for the navbar.
            raise_404(T_BAD_IID, result)
            # NOTREACHED

        ### get_issue() should return an edict. fix it here.
        issue = edict(iid=iid, title=i[0], description=i[1], vtype=i[2], kv=i[3])

        return await func(e, issue)

    return loader


@APP.get('/vote-on/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
@APP.use_template(TEMPLATES / 'vote-on.ezt')
async def vote_on_page(election):
    result = await basic_info()
    result.title = 'Vote On Election'
    result.eid = election.eid

    md = election.get_metadata()
    result.e_title = md[1]

    result.issues = election.list_issues()
    result.issue_count = len(result.issues)

    return result


@APP.get('/admin')
@asfquart.auth.require({R.committer})  ### need general solution
@APP.use_template(TEMPLATES / 'admin.ezt')
async def admin_page():
    result = await basic_info()
    result.title = 'Administration'

    with asfpy.stopwatch.Stopwatch():
        # These are lists of EasyDict instances for each Election.
        election = steve.election.Election.open_to_pid(DB_FNAME, result.uid)
        owned = steve.election.Election.owned_elections(DB_FNAME, result.uid)

    result.owned = [ postprocess_election(e) for e in owned ]

    ### owned.owner_name should be based on OWNER_PID. That might not be
    ### "me" because of authz access to manage issues.

    ### should open/keep a PersonDB instance in the APP
    pdb = steve.persondb.PersonDB(DB_FNAME)
    try:
        me = pdb.get_person(result.uid)
    except steve.persondb.PersonNotFound:
        ### the authn'd committer is not in "person"

        result = await basic_info()
        result.title = 'Unknown Person'
        result.pid = result.uid
        # Note: result.uid (and friends) are needed for the navbar.
        raise_404(T_BAD_PID, result)
        # NOTREACHED

    ### the query for OWNED is just for "me", so this is the correct
    ### name at the moment. When authz kicks in ... Nope.
    # me is (name, email)
    for e in result.owned:
        e.owner_name = me[0]

    result.len_election = len(election)
    result.len_owned = len(owned)

    return result


@APP.get('/manage/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
@APP.use_template(TEMPLATES / 'manage.ezt')
async def manage_page(election):
    result = await basic_info()
    result.title = 'Manage an Election'
    result.eid = election.eid

    md = election.get_metadata()
    result.e_title = md[1]

    state = election.get_state()
    result.e_state = state

    result.issues = election.list_issues()
    result.issue_count = len(result.issues)

    return result


@APP.get('/do-open/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
async def do_open_endpoint(election):
    result = await basic_info()

    ### check authz

    ### should open/keep a PersonDB instance in the APP
    pdb = steve.persondb.PersonDB(DB_FNAME)

    # Open the Election.
    election.open(pdb)

    _LOGGER.info(f'User[U:{result.uid}] opened election[E:{election.eid}]')

    _, title, _ = election.get_metadata()
    await flash_success(f'Opened election: {title}')

    # Return to the management page for this Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.get('/do-close/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
async def do_close_endpoint(election):
    result = await basic_info()

    ### check authz

    # Close the Election.
    election.close()

    _LOGGER.info(f'User[U:{result.uid}] closed election[E:{election.eid}]')

    _, title, _ = election.get_metadata()
    await flash_success(f'Closed election: {title}')

    # Return to the management page for this Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.post('/do-add-issue/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
async def do_add_issue_endpoint(election):
    result = await basic_info()

    ### check authz

    form = edict(await quart.request.form)
    print('FORM:', form)

    ### do stuff
    ### add_issue(iid, title, description, vtype, kv)
    ### the IID should be created by add_issue. Do this for now.
    ### does add_issue() return an edict for the added issue?
    issue = edict(iid=steve.crypto.create_id(),
                  title=form.title,
                  )

    _LOGGER.info(f'User[U:{result.uid}] added issue[I:{issue.iid}]'
                 f' to election[E:{election.eid}]')

    await flash_success(f'Issue "{issue.title}" has been added.')

    # Return to the management page for this Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.post('/do-edit-issue/<eid>/<iid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election_issue
async def do_edit_issue_endpoint(election, issue):
    result = await basic_info()

    ### check authz

    form = edict(await quart.request.form)
    print('FORM:', form)

    # Update the title/description.
    ### for now, no way to update the vtype or KV pairs.
    election.add_issue(issue.iid, form.title, form.description,
                       issue.vtype, issue.kv)

    _LOGGER.info(f'User[U:{result.uid}] edited issue[I:{issue.iid}]'
                 f' in election[E:{election.eid}]')

    # Use the new TITLE for this.
    await flash_success(f'Issue "{form.title}" has been updated.')

    # Return to the management page for this Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.post('/do-delete-issue/<eid>/<iid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election_issue
async def do_delete_issue_endpoint(election, issue):
    result = await basic_info()

    ### check authz

    # Issue exists, and was loaded. No errors to handle?
    election.delete_issue(issue.iid)

    _LOGGER.info(f'User[U:{result.uid}] deleted issue[I:{issue.iid}]'
                 f' from election[E:{election.eid}]')

    await flash_success(f'Issue "{issue.title}" has been deleted.')

    # Return to the management page for this Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.get('/profile')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template(TEMPLATES / 'profile.ezt')
async def profile_page():
    result = await basic_info()
    result.title = 'Profile'

    return result


@APP.get('/settings')
@asfquart.auth.require  # Bare decorator means just require a valid session
@APP.use_template(TEMPLATES / 'settings.ezt')
async def settings_page():
    result = await basic_info()
    result.title = 'Settings'

    return result


@APP.get('/privacy')
@APP.use_template(TEMPLATES / 'privacy.ezt')
async def privacy_page():
    result = await basic_info()
    result.title = 'Privacy'

    return result


@APP.get('/about')
@APP.use_template(TEMPLATES / 'about.ezt')
async def about_page():
    result = await basic_info()
    result.title = 'About'

    return result


# Route to serve static files (CSS and JS)
@APP.route('/static/<path:filename>')
async def serve_static(filename):
    return await quart.send_from_directory(THIS_DIR / 'static', filename)
@APP.route('/favicon.ico')
async def serve_favicon():
    return await quart.send_from_directory(THIS_DIR / 'static', 'favicon.ico')


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

    # note: an election has a third Edit state: not open, not closed;
    # this is called "editable" (S_EDITABLE)

    # Format dates, if present.
    dt_open = e.open_at and datetime.datetime.fromtimestamp(e.open_at)
    e.fmt_open_at = format_datetime(dt_open)
    e.fmt_open_at_full = dt_open and dt_open.strftime(FMT_DATE_FULL)
    dt_close = e.close_at and datetime.datetime.fromtimestamp(e.close_at)
    e.fmt_close_at = format_datetime(dt_close)
    e.fmt_close_at_full = dt_close and dt_close.strftime(FMT_DATE_FULL)

    ### temporary. need to adjust input query.
    if 'owner_pid' not in e:
        e.owner_pid = 'gstein'  ### fix query. for now, could be result.uid
    if 'issue_count' not in e:
        e.issue_count = 5  ### arbitrary. just provide a value

    return e


def raise_404(template, data):
    content = asfquart.utils.render(template, data)
    quart.abort(quart.Response(content, status=404, mimetype='text/html'))
