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
    9/3/16  Fairly working now. Livescrape update has browser-like user agent.

    TODO :  pictures (unravel irritating gallery function?)
            comments
            generalise. Make it work with any cmpatible news site
            index pages, only works w front page atm  
"""

from flask import Flask, request, session, url_for, redirect, \
     render_template, abort, g, flash, _app_ctx_stack
from livescrape import ScrapedPage, CssMulti, Css, CssLink
from sqlite3 import dbapi2 as sqlite3
from datetime import datetime
import time

DATABASE = 'newspapers.db'
DEBUG = False
#DEBUG = True

#domainName = 'http://www.courier.co.uk'
domainName = 'http://leicestermercury.co.uk'
#domainName = 'http://www.bristolpost.co.uk'
newsUrl = '/news'

#domainName = 'http://95.85.37.86'
#newsUrl = '/news.html'
userAgent = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'}

lettersUrl = '/letters'

newsIndexPattern = {
    'block' : '.media__body',
    'blocktitle' : 'a',
    #'title' : 'a',
    'url' : 'a',
    'trail' : '.standfirst' }	# allow config changes / use on other sites

newsStoryPattern = {
    'title' : '.heading--xl , #main-article p',
    'story' : '#main-article p',
    'comments' : '.comment-detail p'
    }

lettersIndexPattern = {'block' : '.channel-list-item.media.cf',
    'blocktitle' : 'a',
    'url' : 'a', 
    'title' : '.media__body h3',
    'trail' : '.standfirst' }	# allow config changes / use on other sites

letterPattern = {
    'title' : 'header h1,heading heading--xl',
    'letter' : '#main-article p',
    'comments' : '.comment-detail p'
    }

storyMaxAge = 10	# max age in mins of index page before it gets checked again


# create our little application :)
app = Flask(__name__, static_url_path = '/static')
app.config.from_object(__name__)
app.config.from_envvar('SANITISER_SETTINGS', silent=True)

class story(object):
    def __init__(self, title, story):
        self.title = title
        self.story = story


class newspaperIndexPage(ScrapedPage):
    scrape_url = domainName + newsUrl
    scrape_headers = userAgent
    stories = CssMulti(newsIndexPattern['block'], 
        title = Css(newsIndexPattern['blocktitle']), 
        trail = Css(newsIndexPattern['trail']),
        url = Css(newsIndexPattern['url'],  attribute='href'),
    )

class newspaperStoryPage(ScrapedPage):
    scrape_headers = userAgent
    title = Css(newsStoryPattern['title']) 
    story = Css(newsStoryPattern['story'], multiple = True )
    comments = Css(newsStoryPattern['comments'])
    timestamp = ''
    
class lettersIndexPage(ScrapedPage):
    scrape_url = domainName + lettersUrl
    scrape_headers = userAgent
    letters = CssMulti(lettersIndexPattern['block'], 
        title = Css(lettersIndexPattern['blocktitle']), 
        trail = Css(lettersIndexPattern['trail']),
        url = Css(lettersIndexPattern['url'],  attribute='href'),)

class newspaperLetterPage(ScrapedPage):
    scrape_headers = userAgent
    title = Css(letterPattern['title'])
    letter = Css(letterPattern['letter'], multiple = True)
    comments = Css(letterPattern['comments'], multiple = True)
    timestamp = ''

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

def getNewestDb(type):
    # returns unix time of newest record
    db = get_db()
    ret = ''
    if type == 'news': 
        ret = query_db('''select strftime('%s',timestamp) from story_index 
        order by timestamp desc limit 1;''', one=True)
    elif type == 'letters':
        ret = query_db('''select strftime('%s',timestamp) from letter_index 
               order by timestamp desc limit 1;''', one=True)
    else:
        print " type not found, 0"
        return 0
    if not ret:
        print " returning 0"
        return 0
    return ret[0]

def saveIndex(stories, table):
    # save the index page
    db = get_db()
    selectQuery = 'select url from ' + table + ' where '
    deleteQuery = 'delete from ' + table + ' where '
    insertQuery = 'insert into ' + table
    for story in stories:
        # if story already exists, delete it and refresh
        c = query_db(selectQuery + 'url=(?)', (story['url'],))
        print "saveIndex - saving ", story['url']
        if c:
            db.execute(deleteQuery + " url=(?)", (story['url'],))
        db.execute(insertQuery + ' (url, title, trail) values (?, ?, ?);', 
              (story['url'], story['title'], story['trail']))
        db.commit()

def saveItem(url, title, story_text, story_comments, itemType):
    # print "saveItem title: ", title, " story_text: ", story_text
    # check if item already in the db
    db = get_db()
    if itemType == 'story':
        c = query_db('select id from stories where url=(?);', (url,))
    elif itemType == 'letter':
        c = query_db('select id from letters where url=(?);', (url,))       
    else:
        print "unknown item type: %s", itemType
        return None
    
    if c:
        # check if story already in db. Should be redundant code
        print "%s already in db. Url = %s" % (itemType, url)
        return
    # save story and url
    story = ''
    for line in story_text:
        story += '<p>' + line + '</p>'
        
    '''
    comments = ''
    for line in story_comments:
        comments += '<p>' + line + '</p>' '''
    print "saveItem commments = ", story_comments
        
    if itemType == 'story':
        db.execute("""insert into stories(url, title, story, comments) 
        values (?, ?, ?, ?);""", (url, title, story, story_comments) )
    elif itemType == 'letter':
        if (story_comments):
            story_comments = story_comments[0]
            db.execute("""insert into letters(url, title, letter, comments) 
            values (?, ?, ?, ?);""", (url, title, story, story_comments) )
        else:
            print "itemType unknown"
            return None
        
    db.commit()

@app.route('/')
@app.route('/<int:page>')
def newsIndex(page = 0):
    # page will be used to get page n from source site
    # get age of newest record
    newestDbTime = int(getNewestDb('news'))
    # get current time
    timeNow = int(time.time())
    # compare
    # print "newestDbTime = %s, timeNow = %s, difference = %s mins" % (newestDbTime,timeNow, (timeNow-newestDbTime)/60)
    if (newestDbTime == 0) or (timeNow - newestDbTime > (storyMaxAge * 60)): 
    # stories are old
    # or db is new
        url = newsUrl + '?page=%s' % (page)
        message = 'Fresh stories from %s updated %s' % (
            domainName + url, datetime.fromtimestamp(newestDbTime))
        stories = newspaperIndexPage().stories
        saveIndex(stories, 'story_index')
    else:	# serve stories from the db   
        message = 'Cached stories from %s updated %s' % (
            domainName + newsUrl, datetime.fromtimestamp(newestDbTime))
        stories = query_db('''select url, title, trail 
            from story_index 
            where timestamp >= datetime('now', '%s minutes')
            order by timestamp asc''' % (-storyMaxAge) )
    return render_template('storiesIndex.html', 
        stories = stories, message = message)

@app.route('/about')
def aboutPage():
    return render_template('about.html')


@app.route('/s/<path:url>')	# get page by original url
def getStory(url):
    '''
    Check the cache. 
    if we don't have the requested story
        get the story
        save it
        serve story from the db
    '''
    message = ''   
    comments = ''
    url = '/' + url

    story = query_db('''select story_index.title, stories.story, stories.comments, stories.timestamp
        from story_index, stories
        where story_index.url = (?)
        and story_index.url = stories.url;
        ''', (url,), one=True)
    if story:
        print story
        # story exists in the db
        print "Story found in db"
        message = "From db %s" % (story[3])
    else:
        # get it
        print "No story in db, fetching from ", domainName + url
        message = 'Live story'
        story = newspaperStoryPage(scrape_url=domainName + url)
        # save it
        print ("fetched story. story.title = ", story.title, 
            " story.text = ", story.story, 
            "stories.comments = ", story.comments)
        saveItem(url, story.title, story.story, story.comments, 'story')
        story = query_db('''select story_index.title, stories.story, stories.comments, stories.timestamp
        from story_index, stories
        where story_index.url = (?)
        and story_index.url = stories.url;
        ''', (url,), one=True)
    return render_template('show_story.html', story = story, message = message, comments = comments, url = domainName + url)

@app.route('/l/<path:url>')	# get page by original url
def getLetter(url):
    '''
    Check the cache. 
    if we don't have the requested letter[5~
        get the letter
        save it
        serve letter from the db
    '''
    message = '' 
    comments = ''  
    url = '/' + url

    letter = query_db('''select letter_index.title, letters.letter, letters.comments, letters.timestamp
        from letter_index, letters
        where letter_index.url = (?)
        and letter_index.url = letters.url;
        ''', (url,), one=True)
    if not letter:
        # get it
        print "No letter in db, fetching"
        message = 'Live letter'
        letter = newspaperLetterPage(scrape_url=domainName + url)
        # save it
        print "fetched letter. letter.title = ", letter.title, " letter.text = ", letter.letter, "letter.comments = ", letter.comments
        saveItem(url, letter.title, letter.letter, letter.comments, 'letter')
        letter = query_db('''select letter_index.title, letters.letter, letters.comments
        from letter_index, letters
        where letter_index.url = (?)
        and letter_index.url = letters.url;
        ''', (url,), one=True)
    else:
        # letter exists in the db
        print "Letter found in db"
        message = "From db %s" % (letter[3])
    return render_template('show_letter.html', letter = letter, message = message, comments = comments, url = domainName + url)
        
@app.route('/letters')
def lettersIndex(page = 0):
    # get age of newest record
    newestDbTime = int(getNewestDb('letters'))
    # get current time
    timeNow = int(time.time())
    # compare
    print "newestDbTime = %s, timeNow = %s, difference = %s mins" % (newestDbTime,timeNow, (timeNow-newestDbTime)/60)
    if (newestDbTime == 0) or (timeNow - newestDbTime > (storyMaxAge * 60)): 
            # stories are old
	    # or db is new
        url = lettersUrl + '?page=%s' % (page)
        message = 'fresh letters from %s' % (domainName + lettersUrl)
        letters = lettersIndexPage(scraped_page = domainName+lettersUrl).letters
        saveIndex(letters, 'letter_index')
    else:       # serve letters from the db
        message = 'Cached letters from %s' % (domainName + lettersUrl)
        message = 'Cached letters from %s updated %s' % (
            domainName + newsUrl, datetime.fromtimestamp(newestDbTime))
        
        letters = query_db('''select url, title, trail
            from letter_index
            where timestamp >= datetime('now', '%s minutes')
            order by timestamp asc''' % (-storyMaxAge) )
    return render_template('lettersIndex.html', letters = letters, message = message)


if __name__ == '__main__':
    # init_db()
    app.run(host='0.0.0.0')

