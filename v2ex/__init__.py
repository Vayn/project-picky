import os

TWITTER_API_ROOT = 'https://twitter.com/'

if (os.environ['SERVER_NAME'] == 'localhost'):
  TWITTER_API_ROOT = 'http://api.dabr.in/'