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

import quart
import asfquart
APP = asfquart.APP


@APP.get('/')
@APP.use_template('templates/home.ezt')
async def home_page():
    return {
        'title': 'Home',
    }


@APP.get('/voter')
@APP.use_template('templates/voter.ezt')
async def voter_page():
    return {
        'title': 'Voting',
    }


@APP.get('/admin')
@APP.use_template('templates/admin.ezt')
async def admin_page():
    return {
        'title': 'Administration',
    }


@APP.get('/profile')
@APP.use_template('templates/profile.ezt')
async def profile_page():
    return {
        'title': 'Profile',
    }


@APP.get('/settings')
@APP.use_template('templates/settings.ezt')
async def settings_page():
    return {
        'title': 'Settings',
    }


@APP.get('/sign-out')
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
