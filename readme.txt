Working out css selectors - http://lxml.de/cssselect.html


import requests
from bs4 import BeautifulSoup

user_agent = {'User-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64;rv:44.0) Gecko/20100101 Firefox/44.0'}
url = 'http://www.leicestermercury.co.uk/letters'
r = requests.get(url, headers=user_agent)
soup = BeautifulSoup(r.text)
print soup.select('h3')



Letters index page
-- get title
print soup.select('#channel-activity-results li article div h3 a')[3].text
Cuts unfairly target disabled - Mercury Mailbox


-- get url
print soup.select('#channel-activity-results li article div h3 a')[3].get('href')
/Cuts-unfairly-target-disabled/story-28944573-detail/story.html



-- get story
print soup.select('#channel-activity-results li article p')[3].text
<p class="standfirst">Many  disabled people, their carers and families will be concerned and angry at the news that Employment Support Allowance (ESA) in the Work Related Activity...</p>


Letters page

url = 'http://www.leicestermercury.co.uk/Level-playing-field-fly-tippers/story-28944575-detail/story.html'
r = requests.get(url, headers=user_agent)
soup = BeautifulSoup(r.text)  


-- get title
print soup.select('header h1,heading heading--xl')[0].text

-- get letter
for line in soup.select('#main-article p'):
   .....:       print line.text
   .....: 
How  very commendable of Charnwood Borough Council to adopt a no-tolerance policy on dropping litter ("£1,000 cost of throwing cigar out of car window", Mercury, March 3).
The council street warden is to be congratulated on taking the Range Rover number and pursuing this through the courts.
So, come on Charnwood Borough Council and Leicester City Council, let's see you put the same amount of effort into bringing the people who have left rubbish by the ton, burnt out caravans etc., at Red Hill Roundabout and Groby Pool.
They have number plates on their Range Rovers as well.
PS:  Just received today's Mercury and note an estate agent has been fined £1,000 for fly tipping by Charnwood Borough Council (Mercury, March 16). Perhaps we could now see a level playing field for all fly tippers.
M J Everett,   Blaby.


-- get comments
