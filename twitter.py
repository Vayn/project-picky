#!/usr/bin/env python
# coding=utf-8

import os
import time
import datetime
import cgi
import urllib
import wsgiref.handlers
import markdown

from v2ex.picky import Article
from v2ex.picky import Datum

from v2ex.picky import formats as CONTENT_FORMATS
from v2ex import TWITTER_API_ROOT

from v2ex.picky.misc import reminder
from v2ex.picky.misc import message

from v2ex.picky.ext import feedparser
from v2ex.picky.ext import twitter
from v2ex.picky.ext.sessions import Session

from google.appengine.api.labs import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api import users

from django.core.paginator import ObjectPaginator, InvalidPage
from django.utils import simplejson

site_domain = Datum.get('site_domain')
site_name = Datum.get('site_name')
site_author = Datum.get('site_author')
site_slogan = Datum.get('site_slogan')
site_analytics = Datum.get('site_analytics')

user = users.get_current_user()

class TwitterHomeHandler(webapp.RequestHandler):
  def get(self):
    template_values = {}
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    tweets = None
    tweets = memcache.get('twitter_home')
    if tweets is None:
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        tweets = api.GetFriendsTimeline(count = 50)
      except:
        api = None
      if tweets is not None:
        i = 0;
        for tweet in tweets:
          tweets[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
          i = i + 1
        memcache.set('twitter_home', tweets, 120)
      template_values['tweets'] = tweets
    else:
      template_values['tweets'] = tweets
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'twitter.html')
    self.response.out.write(template.render(path, template_values))

class TwitterHomeHandler(webapp.RequestHandler):
  def get(self):
    template_values = {}
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    tweets = None
    tweets = memcache.get('twitter_home')
    if tweets is None:
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        tweets = api.GetFriendsTimeline(count=100)
      except:
        api = None
      if tweets is not None:
        i = 0;
        for tweet in tweets:
          tweets[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
          i = i + 1
        memcache.set('twitter_home', tweets, 120)
      template_values['tweets'] = tweets
    else:
      template_values['tweets'] = tweets
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'twitter.html')
    self.response.out.write(template.render(path, template_values))

class TwitterMentionsHandler(webapp.RequestHandler):
  def get(self):
    template_values = {}
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    tweets = None
    tweets = memcache.get('twitter_mentions')
    if tweets is None:
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        tweets = api.GetReplies()
      except:
        api = None
      if tweets is not None:
        i = 0;
        for tweet in tweets:
          tweets[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
          i = i + 1
        memcache.set('twitter_mentions', tweets, 120)
      template_values['tweets'] = tweets
    else:
      template_values['tweets'] = tweets
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'twitter_mentions.html')
    self.response.out.write(template.render(path, template_values))


class TwitterInboxHandler(webapp.RequestHandler):
  def get(self):
    template_values = {}
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    tweets = None
    tweets = memcache.get('twitter_inbox')
    if tweets is None:
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        tweets = api.GetDirectMessages()
      except:
        api = None
      if tweets is not None:
        i = 0;
        for tweet in tweets:
          tweets[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
          i = i + 1
        memcache.set('twitter_inbox', tweets, 120)
      template_values['tweets'] = tweets
    else:
      template_values['tweets'] = tweets
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'twitter_inbox.html')
    self.response.out.write(template.render(path, template_values))


class TwitterUserHandler(webapp.RequestHandler):
  def get(self, user):
    template_values = {}
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    tweets = None
    tweets = memcache.get('twitter_user_' + user)
    if tweets is None:
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        tweets = api.GetUserTimeline(user=user, count=100)
      except:
        api = None
      if tweets is not None:
        i = 0;
        for tweet in tweets:
          tweets[i].datetime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(tweet.created_at, '%a %b %d %H:%M:%S +0000 %Y')))
          i = i + 1
        memcache.set('twitter_user_' + user, tweets, 120)
      template_values['tweets'] = tweets
    else:
      template_values['tweets'] = tweets
    template_values['twitter_user'] = tweets[0].user
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'twitter_user.html')
    self.response.out.write(template.render(path, template_values))

  
class TwitterPostHandler(webapp.RequestHandler):
  def post(self):
    tweet = self.request.get('status')
    if tweet != '':
      twitter_account = Datum.get('twitter_account')
      twitter_password = Datum.get('twitter_password')
      api = twitter.Api(username=twitter_account, password=twitter_password)
      try:
        api.PostUpdate(tweet)
      except:
        api = None
    memcache.delete('twitter_home')
    self.redirect('/twitter')
    
def main():
  application = webapp.WSGIApplication([
  ('/twitter', TwitterHomeHandler),
  ('/twitter/home', TwitterHomeHandler),
  ('/twitter/mentions', TwitterMentionsHandler),
  ('/twitter/inbox', TwitterInboxHandler),
  ('/twitter/user/([a-zA-Z0-9\-\_]+)', TwitterUserHandler),
  ('/twitter/post', TwitterPostHandler)
  ],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()