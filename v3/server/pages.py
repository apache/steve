# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to You under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.

### NOTE: the voting handlers require login for ASF committers only.
### Obviously, this is not a general purpose solution. Something for
### the future, to figure out how we'd like to do configuration
### authorization for various install scenarios and authn systems.

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

import steve.election
import steve.crypto
import steve.persondb

APP = asfquart.APP
_LOGGER = logging.getLogger(__name__)

THIS_DIR = pathlib.Path(__file__).resolve().parent
DB_FNAME = THIS_DIR / APP.cfg.db
TEMPLATES = THIS_DIR / 'templates'
STATICDIR = THIS_DIR / 'static'

# Formatted values to inject into templates.
FMT_DATE = '%b %d'
FMT_DATE_FULL = '%Y-%m-%d %H:%M'
SOON_1HOUR = 60 * 60
SOON_CUTOFF = 48 * SOON_1HOUR  # 48 hours, in seconds

T_BAD_EID = APP.load_template(TEMPLATES / 'e_bad_eid.ezt')
T_BAD_IID = APP.load_template(TEMPLATES / 'e_bad_iid.ezt')
T_BAD_PID = APP.load_template(TEMPLATES / 'e_bad_pid.ezt')


async def basic_info():
    """Return base-level EZT template data."""

    basic = edict()

    # Flashes are stored in the Session. Fetch and turn each flash into
    # EasyDict objects for use by templates.
    # NOTE: .flash() is called with (message, category), but the
    #   .get_flashed_messages() returns tuples of (category, message)
    basic.flashes = [
        edict(message=f[1], category=f[0])
        for f in quart.get_flashed_messages(with_categories=True)
    ]

    s = await asfquart.session.read()
    if s:
        basic.update(
            uid=s['uid'],
            name=s['fullname'],
            email=s['email'],
        )
    else:
        # No session.
        basic.update(
            uid=None,
            name=None,
            email=None,
        )

    ### generate a real token and store in the session
    basic.csrf_token = 'placeholder'

    return basic


async def _set_election_date(election, field):
    """Helper to set open_at or close_at on an election, with validation and logging."""
    result = await basic_info()
    ### check authz
    data = await quart.request.get_json()
    date_str = data.get('date')
    if not date_str:
        quart.abort(400, 'Missing date')
    
    # Validate date (basic check)
    try:
        dt = datetime.datetime.fromisoformat(date_str).date()
    except ValueError:
        quart.abort(400, 'Invalid date format')
    
    # Set the date on the election (field is 'open_at' or 'close_at')
    if field == 'open_at':
        election.set_open_at(dt)
    elif field == 'close_at':
        election.set_close_at(dt)
    else:
        quart.abort(400, 'Invalid field')
    
    _LOGGER.info(f'User[U:{result.uid}] set {field} for election[E:{election.eid}] to {date_str}')
    return '', 204


# Define a bunch of helpers for recording "flash" messages in the session.
# Each helper function is:
#    async def flash_FOO(message)
# where FOO is one of the eight Bootstrap alert classes. See:
#    https://getbootstrap.com/docs/5.0/components/alerts/#examples
flash_primary = functools.partial(quart.flash, category='primary')
flash_secondary = functools.partial(quart.flash, category='secondary')
flash_success = functools.partial(quart.flash, category='success')
flash_danger = functools.partial(quart.flash, category='danger')
flash_warning = functools.partial(quart.flash, category='warning')
flash_info = functools.partial(quart.flash, category='info')
flash_light = functools.partial(quart.flash, category='light')
flash_dark = functools.partial(quart.flash, category='dark')


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

    result.open_elections = [postprocess_election(e) for e in election]
    result.upcoming_elections = [postprocess_election(e) for e in steve.election.Election.upcoming_to_pid(DB_FNAME, result.uid)]
    result.past_elections = [ ]  ### TBD

    result.len_open = len(result.open_elections)
    result.len_upcoming = len(result.upcoming_elections)
    result.len_past = len(result.past_elections)

    ### no longer needed? move to navbar?
    result.len_owned = len(owned)

    if result.len_open:
        result.active_tab = 'open'
    elif result.len_upcoming:
        result.active_tab = 'upcoming'
    else:
        result.active_tab = 'past'

    return result


def load_election(func):
    """Decorator to load/pass-argument an Election from EID."""

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
    """Decorator to load/pass-argument an Election from EID."""

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

    result.election = election.get_metadata()
    result.e_title = result.election.title

    # Add more stuff into the Election instance.
    _ = postprocess_election(result.election)

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

    result.owned = [postprocess_election(e) for e in owned]

    ### owned.owner_name should be based on OWNER_PID. That might not be
    ### "me" because of authz access to manage issues.

    ### should open/keep a PersonDB instance in the APP
    pdb = steve.persondb.PersonDB.open(DB_FNAME)
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

    result.election = election.get_metadata()
    result.e_title = result.election.title
    result.e_state = result.election.state

    # Add more stuff into the Election instance.
    _ = postprocess_election(result.election)

    result.issues = election.list_issues()
    result.issue_count = len(result.issues)

    return result


@APP.get('/manage-stv/<eid>/<iid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election_issue
@APP.use_template(TEMPLATES / 'manage-stv.ezt')
async def manage_stv_page(election, issue):
    if issue.vtype != 'stv':
        # This page is just for STV issues. Redirect to the Election
        # management page.
        return quart.redirect(f'/manage/{election.eid}', code=303)

    result = await basic_info()
    result.title = 'Manage an STV Issue'
    result.eid = election.eid
    result.issue = issue

    result.election = election.get_metadata()
    result.e_title = result.election.title
    result.e_state = result.election.state

    # Add more stuff into the Election instance.
    _ = postprocess_election(result.election)

    kv = edict(issue.kv)
    result.seats = kv.seats

    ### list of candidates. see KV.LABELMAP
    # result.count = len(result.candidates)

    return result


@APP.post('/do-set-open_at/<eid>')
@asfquart.auth.require({R.committer})
@load_election
async def do_set_open_at_endpoint(election):
    return await _set_election_date(election, 'open_at')


@APP.post('/do-set-close_at/<eid>')
@asfquart.auth.require({R.committer})
@load_election
async def do_set_close_at_endpoint(election):
    return await _set_election_date(election, 'close_at')


@APP.post('/do-vote/<eid>')
@asfquart.auth.require({R.committer})
@load_election
async def do_vote_endpoint(election):
    result = await basic_info()

    ### check authz

    # Parse the JSON payload
    data = await quart.request.get_json()
    if not data:
        await flash_danger('No vote data provided.')
        return quart.redirect(f'/vote-on/{election.eid}', code=303)

    # Get the list of issues for this election
    issues = election.list_issues()
    issue_dict = {i.iid: i for i in issues}

    # Process each vote
    for iid, votestring in data.items():
        if iid not in issue_dict:
            await flash_danger(f'Invalid issue ID: {iid}')
            return quart.redirect(f'/vote-on/{election.eid}', code=303)

        try:
            election.add_vote(result.uid, iid, votestring)
            _LOGGER.info(f'User[U:{result.uid}] voted on issue[I:{iid}] in election[E:{election.eid}]')
        except Exception as e:
            _LOGGER.error(f'Error adding vote for user[U:{result.uid}] on issue[I:{iid}]: {e}')
            await flash_danger(f'Error submitting vote for issue {iid}.')
            return quart.redirect(f'/vote-on/{election.eid}', code=303)

    await flash_success('Votes submitted successfully!')
    return quart.redirect(f'/voter', code=303)


@APP.post('/do-create-election')
@asfquart.auth.require({R.pmc_member})  ### need general solution
async def do_create_endpoint():
    "Create a new Election."

    result = await basic_info()

    ### check authz

    form = edict(await quart.request.form)

    # Create the Election.
    election = steve.election.Election.create(DB_FNAME, form.title, result.uid)

    _LOGGER.info(
        f'User[U:{result.uid}] created election[E:{election.eid}];'
        f' title: "{form.title}"'
    )
    await flash_success(f'Created election: {form.title}')

    # Go to the management page for the new Election.
    return quart.redirect(f'/manage/{election.eid}', code=303)


@APP.get('/do-open/<eid>')
@asfquart.auth.require({R.committer})  ### need general solution
@load_election
async def do_open_endpoint(election):
    result = await basic_info()

    ### check authz

    ### should open/keep a PersonDB instance in the APP
    pdb = steve.persondb.PersonDB.open(DB_FNAME)

    # Open the Election.
    election.open(pdb)

    _LOGGER.info(f'User[U:{result.uid}] opened election[E:{election.eid}]')

    title = election.get_metadata().title
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

    title = election.get_metadata().title
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

    ### do better with these
    vtype = 'yna'
    kv = None
    ### for STV, there is a SEATS form parameter. Create empty LABELMAP.

    iid = election.add_issue(form.title, form.description, vtype, kv)

    _LOGGER.info(
        f'User[U:{result.uid}] added issue[I:{iid}] to election[E:{election.eid}]'
    )

    await flash_success(f'Issue "{form.title}" has been added.')

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
    election.edit_issue(issue.iid, form.title, form.description, issue.vtype, issue.kv)

    _LOGGER.info(
        f'User[U:{result.uid}] edited issue[I:{issue.iid}]'
        f' in election[E:{election.eid}]'
    )

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

    _LOGGER.info(
        f'User[U:{result.uid}] deleted issue[I:{issue.iid}]'
        f' from election[E:{election.eid}]'
    )

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
@APP.get('/static/<path:filename>')
async def serve_static(filename):
    return await quart.send_from_directory(STATICDIR, filename)


@APP.get('/favicon.ico')
async def serve_favicon():
    return await quart.send_from_directory(STATICDIR, 'favicon.ico')


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
    # NOTE: side effects. This function manipulates the E argument.

    # Anything but 1 means the Election is not closed.
    e.closed = ezt.boolean(e.closed == 1)

    # We sometimes get IS_OPENED or STATE. Other times, neither.
    # If no open/closed/state information, then we must be EDITABLE.
    if 'is_opened' in e:
        # Anything but 1 means the Election has not been opened.
        e.is_opened = ezt.boolean(e.is_opened == 1)
    elif 'state' not in e:
        e.is_opened = None  # ezt False
    else:
        e.is_opened = ezt.boolean(e.state != steve.election.Election.S_EDITABLE)
    ### note that IS_OPENED is a misnomer since it is True for closed
    ### elections. We should rename it to LOCKED.

    # note: an election has a third Edit state: not open, not closed;
    # this is called "editable" (S_EDITABLE)

    # Format dates, if present.
    dt_open = e.open_at and datetime.datetime.fromtimestamp(e.open_at)
    e.fmt_open_at = format_datetime(dt_open)
    e.fmt_open_at_full = dt_open and dt_open.strftime(FMT_DATE_FULL)
    dt_close = e.close_at and datetime.datetime.fromtimestamp(e.close_at)
    e.fmt_close_at = format_datetime(dt_close)
    e.fmt_close_at_full = dt_close and dt_close.strftime(FMT_DATE_FULL)

    # Add ISO date strings for input fields (YYYY-MM-DD)
    e.fmt_open_at_iso = dt_open.date().isoformat() if dt_open else None
    e.fmt_close_at_iso = dt_close.date().isoformat() if dt_close else None

    ### temporary. need to adjust input query.
    if 'issue_count' not in e:
        e.issue_count = 5  ### arbitrary. just provide a value

    ### need to figure this out later.
    e.has_voted = None  # EZT False

    return e


def raise_404(template, data):
    content = asfquart.utils.render(template, data)
    quart.abort(quart.Response(content, status=404, mimetype='text/html'))
