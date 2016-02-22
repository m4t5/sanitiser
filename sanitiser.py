# -*- coding: utf-8 -*-
"""
    Sanitiser
    ~~~~~~~~

    A newspaper website sanitiser application written with
    Flask and sqlite3. Aim - to retrieve and pass on newspaper
    websites without all the extraneous cruft.

    :copyright: (c) 2016 by Mat Scull.
    :license: BSD, see LICENSE for more details.
    
    9/2/16 Added livescrape code
    10/2/16 Added livescrape
    20/2/16 Updates index page db records
    22/2/16 Problem getting cached from db
    
    Todo:
        sort user agent string - currently python requests, should be firefox
        get read of story index from database working
        get articles from index

"""

from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from livescrape import ScrapedPage, CssMulti, Css, CssLink
from sqlite3 import dbapi2 as sqlite3
import time


#domainName = 'http://www.courier.co.uk'
#domainName = 'http://leicestermercury.co.uk'
domainName = 'http://95.85.37.86'

#newsUrl = '/news'
newsUrl = '/news.html'
lettersUrl = '/letters'

newsPattern = {'block' : '.media__body',
    'blocktitle' : 'a',
    'title' : 'a',
    'url' : 'a',
    'trail' : '.standfirst' }	# allow config changes / use on other sites

lettersPattern =  {'url' : '', 
    'title' : '',
    'trail' : '' }	# allow config changes / use on other sites
storyMaxAge = 1		# max age in mins of index page before it gets checked again


class NewspaperStoryPage(ScrapedPage):
    pass


DATABASE = 'newspapers.db'
DEBUG = True

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('SANISISER_SETTINGS', silent=True)

class story(object):
    def __init__(self, url, heading, storytext):
        self.url = url
        self.heading = heading
        self.storytext = storytext

from livescrape import ScrapedPage, CssMulti, Css, CssLink

class newspaperIndexPage(ScrapedPage):
    scrape_url = domainName + newsUrl
    scrape_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'}
    stories = CssMulti(newsPattern['block'], 
        title = Css(newsPattern['blocktitle']), 
        trail = Css(newsPattern['trail']),
        url = Css(newsPattern['url'],  attribute='href'), #, cleanup=lambda value: value[1:] ) )
    )


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    top = _app_ctx_stack.top
    if not hasattr(top, 'sqlite_db'):
        top.sqlite_db = sqlite3.connect(app.config['DATABASE'])
        top.sqlite_db.row_factory = sqlite3.Row
    return top.sqlite_db


@app.teardown_appcontext
def close_database(exception):
    """Closes the database again at the end of the request."""
    top = _app_ctx_stack.top
    if hasattr(top, 'sqlite_db'):
        top.sqlite_db.close()

def init_db():
    """Creates the database tables."""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def query_db(query, args=(), one=False):
    """Queries the database and returns a list of dictionaries."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv

def getNewestDb():
    # returns unix time of newest record
    db = get_db()
    ret = query_db('''select strftime('%s',timestamp) from story_index 
        order by timestamp desc limit 1;''', one=True)
    if not ret:
        return 0;
    return ret[0]

def saveIndex(stories):
    # save the index page
    db = get_db()
    for story in stories:
        # if story already exists, delete it and refresh
        c = query_db("select url from story_index where url=(?)", (story['url'],))
        #print story['url']
        if c:
            db.execute("delete from story_index where url=(?)", (story['url'],))
        db.execute('''insert into story_index (url, title, trail) 
              values (?, ?, ?);''', 
              (story['url'], story['title'], story['trail']))
        db.commit()

@app.route('/')
@app.route('/<int:page>')
# get index page n
def indexpage(page = 0):
    # page will be used to get page n from source site
    '''
    get latest date on database
    if latestDb - now() < storyAge: # db is fresh
        get stories from db
    else:
        fetch stories from site
        save new stories (check by url)    
    '''
    # get age of newest record
    newestDbTime = int(getNewestDb())
    # get current time
    timeNow = int(time.time())
    # compare
    # print "newestDbTime = %s, timeNow = %s, difference = %s mins" % (newestDbTime,timeNow, (timeNow-newestDbTime)/60)
    if (newestDbTime == 0) or (timeNow - newestDbTime > (storyMaxAge * 60)): # stories are old
    # or db is new
        message = 'fresh stories from %s' % (domainName + newsUrl)
        stories = newspaperIndexPage(domainName + newsUrl).stories
        # problem getting age of page
        saveIndex(stories)
    else:	# serve stories from the db
        # get stories which are less than 24 hours old, order latest first
        message = 'Cached stories'
        '''
        stories = [{'url':'(http://%s) % page',
            'title': ('page number %s requested') % (page),
            'trail' : 'cached page. This is just test data'}]
        '''
        # TODO - get stories with timestamp in the last stoyMaxAge mins
        stories = query_db('''select url, title, trail 
            from story_index 
            where timestamp >= datetime('now', '-(?) minutes')
            order by timestamp asc;''', (storyMaxAge,))
                
    return render_template('show_stories.html', stories = stories, message = message)


@app.route('/s<url>')	# get page by original url
def getStory(url):
    # test data
    '''
    story1 = story('story1.html', 'url requested was: ' + url, 'first post text')
    story2 = story('story2.html', '2nd post', '2nd post text la la la')
    stories = story1, story2
    '''
    print url    
    return render_template('show_stories.html', stories = stories)
		

if __name__ == '__main__':
    #init_db()
    app.run(host='0.0.0.0')
