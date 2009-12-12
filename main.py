#!/usr/bin/env python
# coding=utf-8

import os
import time
import cgi
import wsgiref.handlers

from v2ex.picky import Article
from v2ex.picky import Datum

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api import users

site_domain = Datum.get('site_domain')
site_name = Datum.get('site_name')
site_author = Datum.get('site_author')
site_slogan = Datum.get('site_slogan')
site_updated = Datum.get('site_updated')
if site_updated is None:
  site_updated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

template_values = {
  'site_domain' : site_domain,
  'site_name' : site_name,
  'site_author' : site_author,
  'site_slogan' : site_slogan
}

class MainHandler(webapp.RequestHandler):
  def get(self):
    articles = memcache.get("index")
    if articles is None:
      articles = db.GqlQuery("SELECT * FROM Article WHERE is_page = FALSE ORDER BY created DESC LIMIT 12")
      memcache.add("index", articles, 3600)
    pages = db.GqlQuery("SELECT * FROM Article WHERE is_page = TRUE AND is_for_sidebar = TRUE ORDER BY title ASC")
    template_values['page_title'] = Datum.get('site_name')
    template_values['articles'] = articles
    template_values['articles_total'] = articles.count()
    template_values['pages'] = pages
    template_values['pages_total'] = pages.count()
    template_values['page_archive'] = False
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'index.html')
    self.response.out.write(template.render(path, template_values))

class ArchiveHandler(webapp.RequestHandler):
  def get(self):
    output = memcache.get('archive_output')
    if output is None:  
      articles = memcache.get('archive')
      if articles is None:
        articles = db.GqlQuery("SELECT * FROM Article WHERE is_page = FALSE ORDER BY created DESC")
        memcache.add("archive", articles, 3600)
      pages = db.GqlQuery("SELECT * FROM Article WHERE is_page = TRUE AND is_for_sidebar = TRUE ORDER BY title ASC")
      template_values['page_title'] = site_name + ' Archive'
      template_values['articles'] = articles
      template_values['articles_total'] = articles.count()
      template_values['pages'] = pages
      template_values['pages_total'] = pages.count()
      template_values['page_archive'] = True
      path = os.path.join(os.path.dirname(__file__), 'tpl', 'index.html')
      output = template.render(path, template_values)
      memcache.add('archive_output', output, 1800)
    self.response.out.write(output)
  
class ArticleHandler(webapp.RequestHandler):
  def get(self, url):
    pages = db.GqlQuery("SELECT * FROM Article WHERE is_page = TRUE AND is_for_sidebar = TRUE ORDER BY title ASC")
    article = db.GqlQuery("SELECT * FROM Article WHERE title_url = :1 LIMIT 1", url)
    if (article.count() == 1):
      article_found = True
      article = article[0]
      article.hits = article.hits + 1
      try:
        article.put()
      except:
        article.hits = article.hits - 1
    else:
      article_found = False
    if (article_found):
      parent = None
      if article.parent is not '':
        q = db.GqlQuery("SELECT * FROM Article WHERE title_url = :1 LIMIT 1", article.parent_url)
        if q.count() == 1:
          parent = q[0]
      template_values['parent'] = parent
      template_values['page_title'] = article.title
      template_values['article'] = article
      template_values['pages'] = pages
      template_values['pages_total'] = pages.count()
      path = os.path.join(os.path.dirname(__file__), 'tpl', 'article.html')
      self.response.out.write(template.render(path, template_values))
    else:
      template_values['pages'] = pages
      template_values['pages_total'] = pages.count()
      path = os.path.join(os.path.dirname(__file__), 'tpl', '404.html')
      self.response.out.write(template.render(path, template_values))

class AtomFeedHandler(webapp.RequestHandler):
  def get(self):
    articles = db.GqlQuery("SELECT * FROM Article WHERE is_page = FALSE ORDER BY created DESC LIMIT 20")
    template_values['articles'] = articles
    template_values['articles_total'] = articles.count()
    template_values['site_updated'] = site_updated
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'index.xml')
    self.response.headers['Content-type'] = 'text/xml; charset=UTF-8'
    self.response.out.write(template.render(path, template_values))

class AtomSitemapHandler(webapp.RequestHandler):
  def get(self):
    articles = db.GqlQuery("SELECT * FROM Article ORDER BY last_modified DESC")
    template_values['articles'] = articles
    template_values['articles_total'] = articles.count()
    template_values['site_updated'] = site_updated
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'sitemap.xml')
    self.response.headers['Content-type'] = 'text/xml; charset=UTF-8'
    self.response.out.write(template.render(path, template_values))
    
class RobotsHandler(webapp.RequestHandler):
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'tpl', 'robots.txt')
    self.response.headers['Content-type'] = 'text/plain; charset=UTF-8'
    self.response.out.write(template.render(path, template_values))

def main():
  application = webapp.WSGIApplication([
  ('/archive', ArchiveHandler),
  ('/index.xml', AtomFeedHandler),
  ('/sitemap.xml', AtomSitemapHandler),
  ('/robots.txt', RobotsHandler),
  ('/', MainHandler),
  ('/([0-9a-zA-Z\-\.]+)', ArticleHandler)
  ],
                                       debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()