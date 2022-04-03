#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals
from datetime import date


AUTHOR = u'dev@steve.apache.org'
SITENAME = u'Apache STeVe'
CURRENTYEAR = date.today().year

PATH = 'content'

TIMEZONE = 'UTC'
DEFAULT_DATE = 'fs'
DEFAULT_LANG = u'en'
SITEURL = 'https://steve.apache.org'

# Save pages using full directory preservation
PATH_METADATA= '.*?(pages/)?(?P<path_no_ext>.*?)\.[a-z]*$'
PAGE_SAVE_AS= './{slug}.html'
PAGE_URL= './{slug}.html'


# Sort news by date, descending, latest article first
ARTICLE_ORDER_BY = 'reversed-date'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# TOC Generator
PLUGIN_PATHS = ['./theme/plugins']
PLUGINS = ['toc', 'pelican-gfm',]
TOC_HEADERS = r"h[1-6]"

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('Python.org', 'http://python.org/'),
         ('Jinja2', 'http://jinja.pocoo.org/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('You can add links in your config file', '#'),
          ('Another social link', '#'),)

DEFAULT_PAGINATION = False

