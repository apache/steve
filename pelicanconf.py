
import datetime
# Basic information about the site.
SITENAME = 'Apache STeVe'
SITEDESC = 'Apache STeVe'
SITEDOMAIN = 'steve.apache.org'
SITEURL = 'https://steve.apache.org'
SITELOGO = 'https://steve.apache.org/images/logo.png'
SITEREPOSITORY = 'https://github.com/apache/steve/blob/trunk/site'
CURRENTYEAR = datetime.date.today().year
TRADEMARKS = 'Apache, the Apache feather logo, and "Project" are trademarks or registered trademarks'
TIMEZONE = 'UTC'
# Theme includes templates and possibly static files
THEME = 'theme'
# Specify location of plugins, and which to use
PLUGIN_PATHS = [ '/home/dfoulks/asf/infrastructure-actions/pelican/plugins',  ]
# If the website uses any *.ezmd files, include the 'asfreader' plugin
PLUGINS = [ 'gfm',  ]
# All content is located at '.' (aka content/ )
PAGE_PATHS = [ 'pages' ]
STATIC_PATHS = [ 'css', 'images', 'js',  ]
# Where to place/link generated pages

PATH_METADATA = 'pages/(?P<path_no_ext>.*)\\..*'

PAGE_SAVE_AS = '{path_no_ext}.html'
# Don't try to translate
PAGE_TRANSLATION_ID = None
# Disable unused Pelican features
# N.B. These features are currently unsupported, see https://github.com/apache/infrastructure-pelican/issues/49
FEED_ALL_ATOM = None
INDEX_SAVE_AS = ''
TAGS_SAVE_AS = ''
CATEGORIES_SAVE_AS = ''
AUTHORS_SAVE_AS = ''
ARCHIVES_SAVE_AS = ''
# Disable articles by pointing to a (should-be-absent) subdir
ARTICLE_PATHS = [ 'blog' ]
# needed to create blogs page
ARTICLE_URL = 'blog/{slug}.html'
ARTICLE_SAVE_AS = 'blog/{slug}.html'
# Disable all processing of .html files
READERS = { 'html': None, }








