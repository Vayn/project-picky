import os

TWITTER_API_ROOT = 'http://twitter.com/'

if (os.environ['SERVER_NAME'] == 'localhost'):
  TWITTER_API_ROOT = 'http://yegle.net/s/trunk/'