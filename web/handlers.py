# -*- coding: utf-8 -*-

"""
Main Site Handlers
"""
# standard library imports
import logging, os
import urllib, urllib2, hashlib, httplib2
import json
import datetime
import unicodedata
import re

# related third party imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from web.basehandler import BaseHandler
from web.basehandler import user_required

# google shizzle
from google.appengine.api import taskqueue
from google.appengine.api import channel
from google.appengine.ext import db

# local application/library specific imports
import config
import web.forms as forms
import web.models.models as models
from lib import utils, httpagentparser, captcha
from lib.i18n import get_territory_from_ip
import bleach
import html5lib

# social login
from lib.github import github
from lib.twitter import twitter
from lib.markdown import markdown


class SendEmailHandler(BaseHandler):
    """
    Core Handler for sending Emails
    Use with TaskQueue
    """
    def post(self):

        from google.appengine.api import mail, app_identity
        from google.appengine.api.datastore_errors import BadValueError
        from google.appengine.runtime import apiproxy_errors
        import config
        from models import models

        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        if sender != '' or not utils.is_email_valid(sender):
            if utils.is_email_valid(config.contact_sender):
                sender = config.contact_sender
            else:
                app_id = app_identity.get_application_id()
                sender = "%s <no-reply@%s.appspotmail.com>" % (app_id, app_id)

        try:
            logEmail = models.LogEmail(
                sender = sender,
                to = to,
                subject = subject,
                body = body,
                when = utils.get_date_time("datetimeProperty")
            )
            logEmail.put()
        except (apiproxy_errors.OverQuotaError, BadValueError):
            logging.error("Error saving Email Log in datastore")

        mail.send_mail(sender, to, subject, body)


class ContactHandler(BaseHandler):
    """
    Handler for Contact Form
    """

    def get(self):
        """ Returns a simple HTML for contact form """

        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            if user_info.name or user_info.last_name:
                self.form.name.data = user_info.name + " " + user_info.last_name
            if user_info.email:
                self.form.email.data = user_info.email
        params = {
            "exception" : self.request.get('exception')
            }

        return self.render_template('site/contact.html', **params)

    def post(self):
        """ validate contact form """

        if not self.form.validate():
            return self.get()
        remoteip  = self.request.remote_addr
        user_agent  = self.request.user_agent
        exception = self.request.POST.get('exception')
        name = self.form.name.data.strip()
        email = self.form.email.data.lower()
        message = self.form.message.data.strip()

        try:
            subject = _("Contact")
            # exceptions for error pages that redirect to contact
            if exception != "":
                subject = subject + " (Exception error: %s)" % exception

            template_val = {
                "name": name,
                "email": email,
                "browser": str(httpagentparser.detect(user_agent)['browser']['name']),
                "browser_version": str(httpagentparser.detect(user_agent)['browser']['version']),
                "operating_system": str(httpagentparser.detect(user_agent)['flavor']['name']) + " " +
                                    str(httpagentparser.detect(user_agent)['flavor']['version']),
                "ip": remoteip,
                "message": message
            }
            body_path = "emails/contact.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url = email_url, params={
                'to': config.contact_recipient,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })

            message = _('Your message was sent successfully.')
            self.add_message(message, 'success')
            return self.redirect_to('contact')

        except (AttributeError, KeyError), e:
            logging.error('Error sending contact form: %s' % e)
            message = _('Error sending the message. Please try again later.')
            self.add_message(message, 'error')
            return self.redirect_to('contact')

    @webapp2.cached_property
    def form(self):
        return forms.ContactForm(self)


class channelHandler(BaseHandler):
    def get(self):
        logging.info("some channel thang")
        return


class HomeRequestHandler(BaseHandler):
    def get(self, username=None):
        # load articles in from db and github, stuff them in an array
        articles = models.Article.get_blog_posts(1)

        # loop through all articles
        blogposts = []
        for article in articles:
            # if there's content on Github to serve
            raw_gist_content = github.get_raw_gist_content(article.gist_id)

            # if github gist exists for the entry
            if raw_gist_content:
                article_html = bleach.clean(markdown.markdown(raw_gist_content), config.bleach_tags, config.bleach_attributes)
                article_title = bleach.clean(article.title)
                
                # created and by whom
                date_format = "%a, %d %b %Y"
                created = article.created.strftime(date_format)
                owner_info = models.User.get_by_id(article.owner.id())
                # build entry
                entry = {
                    'created': created,
                    'article_id': article.key.id(),
                    'article_title': article_title,
                    'article_type': article.article_type, 
                    'article_html': article_html,
                    'article_slug': article.slug,
                    'article_owner': owner_info.username,
                    'article_host': self.request.host,
                }   
                blogposts.append(entry)

        # show other recent articles in sidebar
        articles = models.Article.get_blog_posts(5)
        archives = []
        for article in articles:
            owner_info = models.User.get_by_id(article.owner.id())
            article_title = bleach.clean(article.title)
            entry = {
                'article_title': article_title,
                'article_type': article.article_type, 
                'article_slug': article.slug,
                'article_owner': owner_info.username,
                'article_host': self.request.host,
            }
            archives.append(entry)

        # see if we have any blog posts - unlikely we don't
        if len(blogposts) > 0:
            params = {'blogpost': blogposts[0], 'archives': archives} 
        else:
            params = {'blogpost': {} }

        return self.render_template('site/home.html', **params)


class AboutHandler(BaseHandler):
    def get(self):
        params = {}
        return self.render_template('site/about.html', **params)


class ForumsHandler(BaseHandler):
    def get(self):
        params = {}
        return self.render_template('site/forums.html', **params)


class VideosHandler(BaseHandler):
    def get(self):
        params = {}
        return self.render_template('site/videos.html', **params)


class TermsHandler(BaseHandler):
    def get(self):
        params = {}
        return self.render_template('site/terms.html', **params)

