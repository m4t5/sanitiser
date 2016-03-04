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
#newsUrl = '/news'

domainName = 'http://95.85.37.86'
newsUrl = '/news.html'

lettersUrl = '/letters'

newsPattern = {
    'block' : '.media__body',
    'blocktitle' : 'a',
    'title' : 'a',
    'url' : 'a',
    'trail' : '.standfirst' }	# allow config changes / use on other sites

newsStoryPattern = {
    'title' : '.heading--xl , #main-article p',
    'story' : '#main-article p',
    'comments' : '.comment-detail p'
    }


lettersPattern =  {'url' : '', 
    'title' : '',
    'trail' : '' }	# allow config changes / use on other sites
storyMaxAge = 10	# max age in mins of index page before it gets checked again


DATABASE = 'newspapers.db'
DEBUG = True

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)
app.config.from_envvar('SANITISER_SETTINGS', silent=True)

class story(object):
    def __init__(self, title, story):
        self.title = title
        self.story = story


class newspaperIndexPage(ScrapedPage):
    scrape_url = domainName + newsUrl
    scrape_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'}
    stories = CssMulti(newsPattern['block'], 
        title = Css(newsPattern['blocktitle']), 
        trail = Css(newsPattern['trail']),
        url = Css(newsPattern['url'],  attribute='href'),
    )

class newspaperStoryPage(ScrapedPage):
    scrape_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'}
    title = Css(newsStoryPattern['title']) 
    story = Css(newsStoryPattern['story'], multiple=True )
    comments = Css(newsStoryPattern['comments'])
    

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

def saveStory(url, title, story_text):
    db = get_db()
    c = query_db('select id from stories where url=(?);', (url,))
    if c:
        # check if story already in db. Should be redundant code
        print "Story already in db. Url = ", url
        return
    # save story and url
    story = ''
    for line in story_text:
        story += line
    
    db.execute("""insert into stories(url, title, story)
        values (?, ?, ?);""", 
        (url, title, story) 
    )
    db.commit()
                                
@app.route('/')
@app.route('/<int:page>')
def indexpage(page = 0):
    # page will be used to get page n from source site

    # get age of newest record
    newestDbTime = int(getNewestDb())
    # get current time
    timeNow = int(time.time())
    # compare
    # print "newestDbTime = %s, timeNow = %s, difference = %s mins" % (newestDbTime,timeNow, (timeNow-newestDbTime)/60)
    if (newestDbTime == 0) or (timeNow - newestDbTime > (storyMaxAge * 60)): # stories are old
    # or db is new
        message = 'fresh stories from %s' % (domainName + newsUrl)
        stories = newspaperIndexPage().stories
        saveIndex(stories)
    else:	# serve stories from the db
        message = 'Cached stories from %s' % (domainName + newsUrl)
        stories = query_db('''select url, title, trail 
            from story_index 
            where timestamp >= datetime('now', '%s minutes')
            order by timestamp asc''' % (-storyMaxAge) )
                
    return render_template('show_stories.html', stories = stories, message = message)

@app.route('/s/<path:url>')	# get page by original url
def getStory(url):
    '''
    Check the cache. 
    if we don't have the requested story
        get the story
        save it
    serve story from the db
    '''
    url = '/' + url
    # this currently returns a 2 story list. I want story.title and story.text
    story = query_db('''select story_index.title, stories.story
        from story_index, stories
        where story_index.url = (?)
        and story_index.url = stories.url;
        ''', (url,), one=True)
    if not story:
        message = 'Fresh story.'
        # get it
        print "No story in db, fetching"
        story = newspaperStoryPage(scrape_url=domainName + url)
        # save it
        #print "fetched story. story.title = ", story.title, " story.text = ", story.story
        saveStory(url, story.title, story.story)
        story = query_db('''select story_index.title, stories.story
        from story_index, stories
        where story_index.url = (?)
        and story_index.url = stories.url;
        ''', (url,), one=True)
    # story exists in the db
    print "Story found in db"
    message = "From db."
    return render_template('show_story.html', story = story, message = message, url = domainName + url)
        

if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0')
