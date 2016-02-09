# -*- coding: utf-8 -*-
"""
    Sanitiser
    ~~~~~~~~

    A newspaper website sanitiser application written with
    Flask and sqlite3. Aim - to retrieve and pass on newspaper
    websites without all the extraneous cruft.

    :copyright: (c) 2016 by Mat Scull.
    :license: BSD, see LICENSE for more details.
"""

import time
from sqlite3 import dbapi2 as sqlite3
from hashlib import md5
from datetime import datetime
from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from werkzeug import check_password_hash, generate_password_hash

# configuration
DATABASE = 'sanitiser.db'
PER_PAGE = 30
DEBUG = True
SECRET_KEY = 'development key'


domainName = 'http://www.courier.co.uk'
'''
domainName = 'http://leicestermercury.co.uk'
newsUrl = '/news'
'''
lettersUrl = '/letters'


# TODO - sort BS4 search patterns
newsPattern	= ''	# allow config changes / use on other sites
lettersPattern = ''


# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('SANISISER_SETTINGS', silent=True)

class story(object):
	def __init__(self, url, heading, storytext):
		self.url = url
		self.heading = heading
		self.storytext = storytext
	

@app.route('/')
@app.route('/<int:page>')
# get index page n
def indexpage(page = 0):
	# page will be used to get page n from source site
	# test data
	stories = {story(('http://%s') % page, 'page 2', 'page 2 text')}
	return render_template('show_story.html', stories = stories)


@app.route('/s/<url>')	# get page by original url
# eg http://www.leicestermercury.co.uk/Narborough-Road-home-united-nations-shopkeepers/story-28679007-detail/story.html
# probably need to swap '/' for '_'
def getStory(url):
	# test data
	story1 = story('story1.html', 'url requested was: ' + url, 'first post text')
	story2 = story('story2.html', '2nd post', '2nd post text la la la')
	stories = story1, story2
	return render_template('show_stories.html', stories = stories)
		


if __name__ == '__main__':
    app.run(host='0.0.0.0')
