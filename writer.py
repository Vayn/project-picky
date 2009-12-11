#!/usr/bin/env python
# coding=utf-8

import os
import time
import cgi
import urllib
import wsgiref.handlers

from v2ex.picky import Article
from v2ex.picky import Datum
from v2ex.picky.misc import reminder
from v2ex.picky.misc import message
from v2ex.picky.ext import feedparser
from v2ex.picky.ext import twitter

from google.appengine.api.labs import taskqueue
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api import users

from django.core.paginator import ObjectPaginator, InvalidPage

site_domain = Datum.get('site_domain')
site_name = Datum.get('site_name')
site_author = Datum.get('site_author')
site_slogan = Datum.get('site_slogan')

user = users.get_current_user()

# GLOBALS

PAGE_SIZE = 10

class WriterOverviewHandler(webapp.RequestHandler):
  def get(self):
    articles = Article.all().order("-created")
    paginator = ObjectPaginator(articles, PAGE_SIZE)
    try:
      page = int(self.request.get('page', 0))
      articles = paginator.get_page(page)
    except InvalidPage:
      articles = paginator.get_page(int(paginator.pages - 1))
    if paginator.pages > 1:
      is_paginated = True
    else:
      is_paginated = False
    if site_domain is None or site_name is None or site_author is None:
      site_configured = False
    else:
      site_configured = True
    template_values = {
      'site_configured' : site_configured,
      'is_paginated' : is_paginated,
      'page_size' : PAGE_SIZE,
      'page_has_next' : paginator.has_next_page(page),
      'page_has_previous' : paginator.has_previous_page(page),
      'page' : page + 1,
      'next' : page + 1,
      'previous' : page - 1,
      'pages' : paginator.pages,
      'articles' : articles,
      'articles_total' : len(articles)
    }
    if user is not None:
      template_values['user_email'] = user.email()

    mentions_web = memcache.get('mentions_web')
    if mentions_web is None:
      try:
        mentions_web = feedparser.parse('http://blogsearch.google.com/blogsearch_feeds?hl=en&q=' + urllib.quote('link:' + Datum.get('site_domain')) + '&ie=utf-8&num=10&output=atom')
        memcache.add('mentions_web', mentions_web, 3600)
      except:
        mentions_web = None
    if mentions_web is not None:
      if len(mentions_web.entries) > 0:
        template_values['mentions_web'] = mentions_web.entries
    
    mentions_twitter = memcache.get('mentions_twitter')
    if mentions_twitter is None:
      try:
        mentions_twitter = feedparser.parse('https://search.twitter.com/search.atom?q=' + urllib.quote(Datum.get('site_domain')))
        memcache.add('mentions_twitter', mentions_twitter, 3600)
      except:
        mentions_twitter = None
    if mentions_twitter is not None:
      if len(mentions_twitter.entries) > 0:
        template_values['mentions_twitter'] = mentions_twitter.entries
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'overview.html')
    self.response.out.write(template.render(path, template_values))

class WriterSettingsHandler(webapp.RequestHandler):
  def get(self):
    site_domain = Datum.get('site_domain')
    site_name = Datum.get('site_name')
    site_author = Datum.get('site_author')
    site_slogan = Datum.get('site_slogan')
    twitter_account = Datum.get('twitter_account')
    twitter_password = Datum.get('twitter_password')
    twitter_sync = None
    q = db.GqlQuery("SELECT * FROM Datum WHERE title = 'twitter_sync'")
    if q.count() == 1:
      twitter_sync = q[0].substance
    if (twitter_sync == 'True'):
      twitter_sync = True
    else:
      twitter_sync = False
    template_values = {
      'site_domain' : site_domain,
      'site_name' : site_name,
      'site_author' : site_author,
      'site_slogan' : site_slogan,
      'twitter_account' : twitter_account,
      'twitter_password' : twitter_password,
      'twitter_sync' : twitter_sync
    }
    if user is not None:
      template_values['user_email'] = user.email()
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'settings.html')
    self.response.out.write(template.render(path, template_values))
    
  def post(self):
    Datum.set('site_domain', self.request.get('site_domain'))
    Datum.set('site_name', self.request.get('site_name'))
    Datum.set('site_author', self.request.get('site_author'))
    Datum.set('site_slogan', self.request.get('site_slogan'))
    Datum.set('twitter_account', self.request.get('twitter_account'))
    Datum.set('twitter_password', self.request.get('twitter_password'))
    
    q = db.GqlQuery("SELECT * FROM Datum WHERE title = 'twitter_sync'")
    if q.count() == 1:
      twitter_sync = q[0]
    else:
      twitter_sync = Datum()
      twitter_sync.title = 'twitter_sync'
    twitter_sync.substance = self.request.get('twitter_sync')
    if twitter_sync.substance == 'True':
      twitter_sync.substance = 'True'
    else:
      twitter_sync.substance = 'False'
    twitter_sync.put()
    
    self.redirect('/writer/settings')
    
class WriterWriteHandler(webapp.RequestHandler):
  def get(self, key = ''):
    if (key):
      article = db.get(db.Key(key))
      template_values = {
        'article' : article,
        'page_mode' : 'edit',
        'page_title' : 'Edit Article',
        'page_reminder': reminder.writer_write
      }
    else:
      template_values = {
        'page_mode' : 'new',
        'page_title' : 'New Article',
        'page_reminder': reminder.writer_write
      }
    if user is not None:
      template_values['user_email'] = user.email()
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'write.html')
    self.response.out.write(template.render(path, template_values))

class WriterRemoveHandler(webapp.RequestHandler):
  def get(self, key = ''):
    if (key):
      article = db.get(db.Key(key))
      article.delete()
    self.redirect('/writer/overview')

class WriterSynchronizeHandler(webapp.RequestHandler):
  def get(self):
    self.redirect('/')
    
  def post(self, key = ''):
    if (self.request.get('content') != ''):
      if (key):
        article = db.get(db.Key(key))
        article.title = self.request.get('title')
        article.title_link = self.request.get('title_link')
        article.title_url = self.request.get('title_url')
        article.parent_url = self.request.get('parent_url')
        article.content = self.request.get('content')
        if (self.request.get('is_page') == 'True'):
          article.is_page = True
        else:
          article.is_page = False
        if (self.request.get('is_for_sidebar') == 'True'):
          article.is_for_sidebar = True
        else:
          article.is_for_sidebar = False
        article.put()
      else:
        article = Article()
        article.title = self.request.get('title')
        article.title_link = self.request.get('title_link')
        article.title_url = self.request.get('title_url')
        article.parent_url = self.request.get('parent_url')
        article.content = self.request.get('content')
        if (self.request.get('is_page') == 'True'):
          article.is_page = True
        else:
          article.is_page = False
        if (self.request.get('is_for_sidebar') == 'True'):
          article.is_for_sidebar = True
        else:
          article.is_for_sidebar = False
        article.put()
        # Ping Twitter
        twitter_sync = Datum.get('twitter_sync')
        if twitter_sync == 'True':  
          twitter_account = Datum.get('twitter_account')
          twitter_password = Datum.get('twitter_password')
          if twitter_account != '' and twitter_password != '':
            api = twitter.Api(username=twitter_account, password=twitter_password)
            try:
              status = api.PostUpdate(article.title + ' http://' + site_domain + '/' + article.title_url)
            except:
              api = None
      memcache.delete('archive')
      memcache.delete('index')
      Datum.set('site_updated', time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
      # Ping Google Blog Search
      try:
        google_ping = 'http://blogsearch.google.com/ping?name=' + urllib.quote(Datum.get('site_name')) + '&url=http://' + urllib.quote(Datum.get('site_domain')) + '/&changesURL=http://' + urllib.quote(Datum.get('site_domain')) + '/sitemap.xml'
        result = urlfetch.fetch(google_ping)
      except:
        taskqueue.add(url='/writer/ping')
      self.redirect('/writer/overview')
    else:
      article = Article()
      article.title = self.request.get('title')
      article.title_link = self.request.get('title_link')
      article.title_url = self.request.get('title_url')
      article.content = self.request.get('content')
      if (self.request.get('is_page') == 'True'):
        article.is_page = True
      else:
        article.is_page = False
      if (self.request.get('is_for_sidebar') == 'True'):
        article.is_for_sidebar = True
      else:
        article.is_for_sidebar = False
      template_values = {
        'article' : article,
        'page_mode' : 'new',
        'page_title' : 'New Article',
        'page_reminder': reminder.writer_write,
        'message' : message.content_empty,
        'user_email' : user.email()
      }
      path = os.path.join(os.path.dirname(__file__), 'tpl', 'writer', 'write.html')
      self.response.out.write(template.render(path, template_values))
      
class WriterPingHandler(webapp.RequestHandler):
  def get(self):
    try:
      google_ping = 'http://blogsearch.google.com/ping?name=' + urllib.quote(Datum.get('site_name')) + '&url=http://' + urllib.quote(Datum.get('site_domain')) + '/&changesURL=http://' + urllib.quote(Datum.get('site_domain')) + '/index.xml'
      result = urlfetch.fetch(google_ping)
      if result.status_code == 200:
        self.response.out.write('OK: Google Blog Search Ping: ' + google_ping)
      else:
        self.response.out.write('Reached but failed: Google Blog Search Ping: ' + google_ping)
    except:
      self.response.out.write('Failed: Google Blog Search Ping: ' + google_ping)
  
def main():
  application = webapp.WSGIApplication([
  ('/writer', WriterOverviewHandler),
  ('/writer/overview', WriterOverviewHandler),
  ('/writer/settings', WriterSettingsHandler),
  ('/writer/new', WriterWriteHandler),
  ('/writer/save', WriterSynchronizeHandler),
  ('/writer/ping', WriterPingHandler),
  ('/writer/update/([0-9a-zA-Z\-]+)', WriterSynchronizeHandler),
  ('/writer/edit/([0-9a-zA-Z\-]+)', WriterWriteHandler),
  ('/writer/remove/([0-9a-zA-Z\-]+)', WriterRemoveHandler)
  ],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()