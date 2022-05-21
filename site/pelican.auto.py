
# Basic information about the site.
SITENAME = 'Apache STeVe'
SITEDESC = 'Apache STeVe'
SITEDOMAIN = 'steve.apache.org'
SITEURL = 'https://steve.apache.org'
SITELOGO = 'https://steve.apache.org/images/logo.png'
SITEREPOSITORY = 'https://github.com/apache/steve/blob/trunk/site'
CURRENTYEAR = 2022
TRADEMARKS = 'Apache, the Apache feather logo, and "Project" are trademarks or registered trademarks'
TIMEZONE = 'UTC'
# Theme includes templates and possibly static files
THEME = '/home/gstein/src/asf/steve/site/theme'
# Specify location of plugins, and which to use
PLUGIN_PATHS = [ '/home/gstein/src/asf/i-pelican/bin/../plugins',  ]
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
FEED_ALL_ATOM = None
INDEX_SAVE_AS = ''
TAGS_SAVE_AS = ''
CATEGORIES_SAVE_AS = ''
AUTHORS_SAVE_AS = ''
ARCHIVES_SAVE_AS = ''
# Disable articles by pointing to a (should-be-absent) subdir
ARTICLE_PATHS = [ 'articles' ]
# Disable all processing of .html files
READERS = { 'html': None, }






