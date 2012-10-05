# -*- coding: utf-8 -*-

"""
TinyProbe User Classes.
"""
# standard library imports
import logging
import urllib, urllib2, hashlib, json
from lib.i18n import get_territory_from_ip

# related third party imports
import webapp2
from webapp2_extras import security
from webapp2_extras.auth import InvalidAuthIdError, InvalidPasswordError
from webapp2_extras.i18n import gettext as _
from webapp2_extras.appengine.auth.models import Unique
from google.appengine.api import taskqueue

# local application/library specific imports
import config
import web.forms as forms
import models.models as models
from lib import utils, httpagentparser, captcha
from lib.basehandler import BaseHandler
from lib.basehandler import user_required

# social login
from lib.github import github
from lib.twitter import twitter

class PreRegisterBaseHandler(BaseHandler):
    """
    Base class for handlers with preregistration.
    """
    @webapp2.cached_property
    def form(self):
        return forms.PreRegisterForm(self)


class RegisterBaseHandler(BaseHandler):
    """
    Base class for handlers with registration and login forms.
    """
    @webapp2.cached_property
    def form(self):
        return forms.RegisterForm(self)


class SendEmailHandler(BaseHandler):
    """
    Core Handler for sending Emails
    Use with TaskQueue
    """

    def post(self):
        to = self.request.get("to")
        subject = self.request.get("subject")
        body = self.request.get("body")
        sender = self.request.get("sender")

        utils.send_email(to, subject, body, sender)


class LoginHandler(BaseHandler):
    """
    Handler for authentication
    """

    def get(self):
        """ Returns a simple HTML form for login """

        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('user/login.html', **params)

    def post(self):
        """
        username: Get the username from POST dict
        password: Get the password from POST dict
        """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()

        try:
            if utils.is_email_valid(username):
                user = models.User.get_by_email(username)
                if user:
                    auth_id = user.auth_ids[0]
                else:
                    raise InvalidAuthIdError
            else:
                auth_id = "own:%s" % username
                user = models.User.get_by_auth_id(auth_id)

            password = self.form.password.data.strip()
            remember_me = True if str(self.request.POST.get('remember_me')) == 'on' else False

            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            # Try to login user with password
            # Raises InvalidAuthIdError if user is not found
            # Raises InvalidPasswordError if provided password
            # doesn't match with specified user
            self.auth.get_user_by_password(
                auth_id, password, remember=remember_me)

            # if user account is not activated, logout and redirect to home
            if (user.activated == False):
                # logout
                self.auth.unset_session()

                # redirect to home with error message
                message = _('Your account has been suspended. Please contact support for more information.')
                self.add_message(message, 'error')
                return self.redirect_to('login')

            # REMOVE ME
            #check twitter association in session
            twitter_helper = twitter.TwitterAuth(self)
            twitter_association_data = twitter_helper.get_association_data()
            if twitter_association_data is not None:
                if models.SocialUser.check_unique(user.key, 'twitter', str(twitter_association_data['id'])):
                    social_user = models.SocialUser(
                        user = user.key,
                        provider = 'twitter',
                        uid = str(twitter_association_data['id']),
                        extra_data = twitter_association_data
                    )
                    social_user.put()

            logVisit = models.LogVisit(
                user=user.key,
                uastring=self.request.user_agent,
                ip=self.request.remote_addr,
                timestamp=utils.get_date_time()
            )
            logVisit.put()
            self.redirect_to('home')
        except (InvalidAuthIdError, InvalidPasswordError), e:
            # Returns error message to self.response.write in
            # the BaseHandler.dispatcher
            message = _("Your username or password is incorrect.  Caps lock?")
            self.add_message(message, 'error')
            return self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.LoginForm(self)


class SocialLoginHandler(BaseHandler):
    """
    Handler for Social authentication
    """

    def get(self, provider_name):
        provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']
        if not config.enable_federated_login:
            message = _('Federated login is disabled.')
            self.add_message(message, 'warning')
            return self.redirect_to('login')

        #OAuth Shizzle    
        callback_url = "%s/social_login/%s/complete" % (self.request.host_url, provider_name)
        
        if provider_name == "twitter":
            twitter_helper = twitter.TwitterAuth(self, redirect_uri=callback_url)
            self.redirect( twitter_helper.auth_url() )

        # github stores the callback URL in the app settings on their site, so we don't pass it here
        # you can register a new app at https://github.com/settings/applications/
        elif provider_name == "github":
            scope = ['gist']
            github_helper = github.GithubAuth(scope)
            self.redirect( github_helper.get_authorize_url() )
            
        else:
            message = _('%s authentication is not yet implemented.' % provider_display_name)
            self.add_message(message, 'warning')
            self.redirect_to('edit-profile')


class CallbackSocialLoginHandler(BaseHandler):
    """
    Callback (Save Information) for Social Authentication
    """

    def get(self, provider_name):
        if not config.enable_federated_login:
            message = _('Federated login is disabled.')
            self.add_message(message, 'warning')
            return self.redirect_to('login')

        if provider_name == "twitter":
            oauth_token = self.request.get('oauth_token')
            oauth_verifier = self.request.get('oauth_verifier')
            twitter_helper = twitter.TwitterAuth(self)
            user_data = twitter_helper.auth_complete(oauth_token,
                oauth_verifier)
            if self.user:
                # new association with twitter
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, 'twitter', str(user_data['id'])):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = 'twitter',
                        uid = str(user_data['id']),
                        extra_data = user_data
                    )
                    social_user.put()

                    message = _('Twitter association added.')
                    self.add_message(message, 'success')
                else:
                    message = _('This Twitter account is already in use.')
                    self.add_message(message, 'error')
                self.redirect_to('edit-profile')
            else:
                # login with twitter
                social_user = models.SocialUser.get_by_provider_and_uid('twitter', str(user_data['id']))
                if social_user:
                    # Social user exists. Need authenticate related site account
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    # Social user does not exists. Need show login and registration forms
                    twitter_helper.save_association_data(user_data)
                    message = _('This Twitter account is not associated with a TinyProbe account. '
                                'Please sign in or create a TinyProbe account before continuing.')
                    self.add_message(message, 'warning')
                    self.redirect_to('login')

        # association with github
        # path is something like http://www.tinyprobe.com/social_login/github/
        elif provider_name == "github":
            logging.info("got a request")
            self.redirect_to('home')

        # google, myopenid, yahoo OpenID Providers
        elif provider_name in models.SocialUser.open_id_providers():
            provider_display_name = models.SocialUser.PROVIDERS_INFO[provider_name]['label']
            # get info passed from OpenId Provider
            from google.appengine.api import users
            current_user = users.get_current_user()
            if current_user:
                if current_user.federated_identity():
                    uid = current_user.federated_identity()
                else:
                    uid = current_user.user_id()
                email = current_user.email()
            else:
                message = _('No user authentication information received from %s. '
                            'Please ensure you are logging in from an authorized OpenID Provider (OP).'
                            % provider_display_name)
                self.add_message(message, 'error')
                return self.redirect_to('login')
            if self.user:
                # add social account to user
                user_info = models.User.get_by_id(long(self.user_id))
                if models.SocialUser.check_unique(user_info.key, provider_name, uid):
                    social_user = models.SocialUser(
                        user = user_info.key,
                        provider = provider_name,
                        uid = uid
                    )
                    social_user.put()

                    message = _('%s association successfully added.' % provider_display_name)
                    self.add_message(message, 'success')
                else:
                    message = _('This %s account is already in use.' % provider_display_name)
                    self.add_message(message, 'error')
                self.redirect_to('edit-profile')
            else:
                # login with OpenId Provider
                social_user = models.SocialUser.get_by_provider_and_uid(provider_name, uid)
                if social_user:
                    # Social user found. Authenticate the user
                    user = social_user.user.get()
                    self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
                    logVisit = models.LogVisit(
                        user = user.key,
                        uastring = self.request.user_agent,
                        ip = self.request.remote_addr,
                        timestamp = utils.get_date_time()
                    )
                    logVisit.put()
                    self.redirect_to('home')
                else:
                    message = _('This OpenID based account is not associated with a TinyProbe account. '
                                'Please sign in or create a TinyProbe account before continuing.')
                    self.add_message(message, 'warning')
                    self.redirect_to('login')
        else:
            message = _('This authentication method is not yet implemented!')
            self.add_message(message, 'warning')
            self.redirect_to('login')


class DeleteSocialProviderHandler(BaseHandler):
    """
    Delete Social association with an account
    """

    @user_required
    def get(self, provider_name):
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            social_user = models.SocialUser.get_by_user_and_provider(user_info.key, provider_name)
            if social_user:
                social_user.key.delete()
                message = _('%s successfully disassociated.' % provider_name.title())
                self.add_message(message, 'success')
            else:
                message = _('Social account on %s not found for this user.' % provider_name.title())
                self.add_message(message, 'error')
        self.redirect_to('edit-profile')


class LogoutHandler(BaseHandler):
    """
    Destroy user session and redirect to login
    """

    def get(self):
        if self.user:
            message = _("You've signed out successfully. Warning: Please clear all cookies and logout "
                        "of OpenId providers too if you logged in on a public computer.")
            self.add_message(message, 'info')

        self.auth.unset_session()
        # User is logged out, let's try redirecting to login page
        try:
            self.redirect(self.auth_config['login_url'])
        except (AttributeError, KeyError), e:
            logging.error("Error logging out: %s" % e)
            message = _("User is logged out, but there was an error on the redirection.")
            self.add_message(message, 'error')
            return self.redirect_to('home')


class PreRegisterHandler(PreRegisterBaseHandler):
    def get(self):
        if self.user:
            self.redirect_to('home')
        params = {}
        return self.render_template('user/preregister.html', **params)

    def post(self):
        """ Get fields from POST dict """
        email = self.form.email.data.lower()

        user_info = models.User.get_by_email(email)
        #if (user_info.activated == False):
        if True:
            # send email
            subject =  _("TinyProbe Signup Link")
            encoded_email = utils.encode(email)
            confirmation_url = self.uri_for("register",
                encoded_email = encoded_email,
                _full = True)

            # load email's template
            template_val = {
                "app_name": config.app_name,
                "confirmation_url": confirmation_url,
                "support_url": self.uri_for("contact", _full=True)
            }
            body_path = "emails/email_validation.txt"
            body = self.jinja2.render_template(body_path, **template_val)

            email_url = self.uri_for('taskqueue-send-email')
            taskqueue.add(url = email_url, params={
                'to': str(email),
                'subject' : subject,
                'body' : body,
                })
            logging.info(body)

        message = _('Please check your email for an account activation token.  You can close this page if you like.')
        self.add_message(message, 'info')
        return self.redirect_to('preregister')


class RegisterHandler(RegisterBaseHandler):
    """
    Handler for Sign Up Users
    """

    def get(self, encoded_email=""):
        """ Returns a simple HTML form for create a new user """

        # gravatar goodness
        email = utils.decode(encoded_email)
        gravatar_url = "http://en.gravatar.com/%s.json" % hashlib.md5(email.lower()).hexdigest()
        try:
            data = json.load(urllib2.urlopen(gravatar_url))
            suggested_username = data['entry'][0]['preferredUsername']
        except:
            suggested_username = ""
            logging.info("no data pulled from gravatar")

        if self.user:
            self.redirect_to('home')

        #use the suggested username from gravatar
        params = {"suggested_username": suggested_username}

        return self.render_template('user/register.html', **params)

    def post(self, encoded_email=""):
        """ Get fields from POST dict """

        if not self.form.validate():
            logging.info("didn't validate")
            return self.get(encoded_email)

        username = self.form.username.data.lower()
        email = utils.decode(encoded_email)
        password = self.form.password.data.strip()

        # Password to SHA512
        password = utils.encrypt(password, config.salt)

        # gravatar goodness
        email = utils.decode(encoded_email)
        gravatar_url = "http://en.gravatar.com/%s.json" % hashlib.md5(email.lower()).hexdigest()
        try:
            data = json.load(urllib2.urlopen(gravatar_url))
            firstname = data['entry'][0]['name']['givenName']
            lastname = data['entry'][0]['name']['familyName']
            gravatar_url = data['entry'][0]['photos'][0]['value']
            country = get_territory_from_ip(self)
        except:
            firstname = ""
            lastname = ""
            gravatar_url = ""
            country = get_territory_from_ip(self)
            logging.info("no data pulled from gravatar")

        # Passing password_raw=password so password will be hashed
        # Returns a tuple, where first value is BOOL.
        # If True ok, If False no new user is created
        unique_properties = ['username', 'email']
        auth_id = "own:%s" % username
        user = self.auth.store.user_model.create_user(
            auth_id, unique_properties, password_raw=password,
            username=username, name=firstname, last_name=lastname, email=email,
            ip=self.request.remote_addr, country=country, gravatar_url=gravatar_url, activated=True
        )

        if not user[0]: #user is a tuple
            if "username" in str(user[1]):
                message = _('Sorry, The username %s is already registered.' % '<strong>{0:>s}</strong>'.format(username) )
            elif "email" in str(user[1]):
                message = _('Sorry, The email %s is already registered.' % '<strong>{0:>s}</strong>'.format(email) )
            else:
                message = _('Sorry, The user is already registered.')
            self.add_message(message, 'error')
            return self.redirect_to('register', encoded_email=encoded_email)
        else:
            # If the user didn't register using registration form ???
            db_user = self.auth.get_user_by_password(user[1].auth_ids[0], password)
            
            message = _('Welcome %s, you are now logged in.' % '<strong>{0:>s}</strong>'.format(username) )
            self.add_message(message, 'success')
            return self.redirect_to('home')


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

        return self.render_template('contact.html', **params)

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


class EditProfileHandler(BaseHandler):
    """
    Handler for Edit User Profile
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit profile """

        params = {}

        if self.user:
            logging.info("logged in")
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            logging.info(user_info.name)
            self.form.username.data = user_info.username
            self.form.name.data = user_info.name
            logging.info(user_info.name)
            self.form.last_name.data = user_info.last_name
            self.form.country.data = user_info.country
            providers_info = user_info.get_social_providers_info()
            params['used_providers'] = providers_info['used']
            params['unused_providers'] = providers_info['unused']
            params['country'] = user_info.country
            params['company'] = user_info.company

        return self.render_template('user/edit_profile.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        username = self.form.username.data.lower()
        name = self.form.name.data.strip()
        last_name = self.form.last_name.data.strip()
        country = self.form.country.data

        try:
            user_info = models.User.get_by_id(long(self.user_id))

            try:
                message=''
                # update username if it has changed and it isn't already taken
                if username != user_info.username:
                    user_info.unique_properties = ['username','email']
                    uniques = [
                               'User.username:%s' % username,
                               'User.auth_id:own:%s' % username,
                               ]
                    # Create the unique username and auth_id.
                    success, existing = Unique.create_multi(uniques)
                    if success:
                        # free old uniques
                        Unique.delete_multi(['User.username:%s' % user_info.username, 'User.auth_id:own:%s' % user_info.username])
                        # The unique values were created, so we can save the user.
                        user_info.username=username
                        user_info.auth_ids[0]='own:%s' % username
                        message+= _('Your new username is %s' % '<strong>{0:>s}</strong>'.format(username) )

                    else:
                        message+= _('The username %s is already taken. Please choose another.'
                                % '<strong>{0:>s}</strong>'.format(username) )
                        # At least one of the values is not unique.
                        self.add_message(message, 'error')
                        return self.get()
                user_info.name=name
                user_info.last_name=last_name
                user_info.country=country
                user_info.put()
                message+= " " + _('Thanks, your settings have been saved.  You may now dance.')
                self.add_message(message, 'success')
                return self.get()

            except (AttributeError, KeyError, ValueError), e:
                logging.error('Error updating profile: ' + e)
                message = _('Unable to update profile. Please try again later.')
                self.add_message(message, 'error')
                return self.get()

        except (AttributeError, TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message, 'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditProfileForm(self)


class EditPasswordHandler(BaseHandler):
    """
    Handler for Edit User Password
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for editing password """

        params = {}
        return self.render_template('user/edit_password.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        current_password = self.form.current_password.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username

            # Password to SHA512
            current_password = utils.encrypt(current_password, config.salt)
            try:
                user = models.User.get_by_auth_password(auth_id, current_password)
                # Password to SHA512
                password = utils.encrypt(password, config.salt)
                user.password = security.generate_password_hash(password, length=12)
                user.put()

                # send email
                subject = config.app_name + " Account Password Changed"

                # load email's template
                template_val = {
                    "app_name": config.app_name,
                    "first_name": user.name,
                    "username": user.username,
                    "email": user.email,
                    "reset_password_url": self.uri_for("password-reset", _full=True)
                }
                email_body_path = "emails/password_changed.txt"
                email_body = self.jinja2.render_template(email_body_path, **template_val)
                email_url = self.uri_for('taskqueue-send-email')
                taskqueue.add(url = email_url, params={
                    'to': user.email,
                    'subject' : subject,
                    'body' : email_body,
                    'sender' : config.contact_sender,
                    })

                #Login User
                self.auth.get_user_by_password(user.auth_ids[0], password)
                self.add_message(_('Password changed successfully.'), 'success')
                return self.redirect_to('edit-profile')
            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Incorrect password! Please enter your current password to change your account settings.")
                self.add_message(message, 'error')
                return self.redirect_to('edit-password')
        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message, 'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.EditPasswordMobileForm(self)
        else:
            return forms.EditPasswordForm(self)


class EditEmailHandler(BaseHandler):
    """
    Handler for Edit User's Email
    """

    @user_required
    def get(self):
        """ Returns a simple HTML form for edit email """

        params = {}
        if self.user:
            user_info = models.User.get_by_id(long(self.user_id))
            params['current_email'] = user_info.email

        return self.render_template('user/edit_email.html', **params)

    def post(self):
        """ Get fields from POST dict """

        if not self.form.validate():
            return self.get()
        new_email = self.form.new_email.data.strip()
        password = self.form.password.data.strip()

        try:
            user_info = models.User.get_by_id(long(self.user_id))
            auth_id = "own:%s" % user_info.username
            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            try:
                # authenticate user by its password
                user = models.User.get_by_auth_password(auth_id, password)

                # if the user change his/her email address
                if new_email != user.email:

                    # check whether the new email has been used by another user
                    aUser = models.User.get_by_email(new_email)
                    if aUser is not None:
                        message = _("The email %s is already registered." % new_email)
                        self.add_message(message, 'error')
                        return self.redirect_to("edit-email")

                    # send email
                    subject = _("%s Email Changed Notification" % config.app_name)
                    user_token = models.User.create_auth_token(self.user_id)
                    confirmation_url = self.uri_for("email-changed-check",
                        user_id = user_info.get_id(),
                        encoded_email = utils.encode(new_email),
                        token = user_token,
                        _full = True)

                    # load email's template
                    template_val = {
                        "app_name": config.app_name,
                        "first_name": user.name,
                        "username": user.username,
                        "new_email": new_email,
                        "confirmation_url": confirmation_url,
                        "support_url": self.uri_for("contact", _full=True)
                    }

                    old_body_path = "emails/email_changed_notification_old.txt"
                    old_body = self.jinja2.render_template(old_body_path, **template_val)

                    new_body_path = "emails/email_changed_notification_new.txt"
                    new_body = self.jinja2.render_template(new_body_path, **template_val)

                    email_url = self.uri_for('taskqueue-send-email')
                    taskqueue.add(url = email_url, params={
                        'to': user.email,
                        'subject' : subject,
                        'body' : old_body,
                        })
                    taskqueue.add(url = email_url, params={
                        'to': new_email,
                        'subject' : subject,
                        'body' : new_body,
                        })

                    # display successful message
                    msg = _("Please check your new email for confirmation. Your email will be updated after confirmation.")
                    self.add_message(msg, 'success')
                    return self.redirect_to('edit-profile')

                else:
                    self.add_message(_("You didn't change your email."), "warning")
                    return self.redirect_to("edit-email")


            except (InvalidAuthIdError, InvalidPasswordError), e:
                # Returns error message to self.response.write in
                # the BaseHandler.dispatcher
                message = _("Incorrect password! Please enter your current password to change your account settings.")
                self.add_message(message, 'error')
                return self.redirect_to('edit-email')

        except (AttributeError,TypeError), e:
            login_error_message = _('Sorry you are not logged in.')
            self.add_message(login_error_message,'error')
            self.redirect_to('login')

    @webapp2.cached_property
    def form(self):
        return forms.EditEmailForm(self)


class PasswordResetHandler(BaseHandler):
    """
    Password Reset Handler with Captcha
    """

    reCaptcha_public_key = config.captcha_public_key
    reCaptcha_private_key = config.captcha_private_key

    def get(self):
        chtml = captcha.displayhtml(
            public_key = self.reCaptcha_public_key,
            use_ssl = False,
            error = None)
        params = {'captchahtml': chtml}
        return self.render_template('user/password_reset.html', **params)

    def post(self):
        # check captcha
        challenge = self.request.POST.get('recaptcha_challenge_field')
        response  = self.request.POST.get('recaptcha_response_field')
        remoteip  = self.request.remote_addr

        cResponse = captcha.submit(
            challenge,
            response,
            self.reCaptcha_private_key,
            remoteip)

        if cResponse.is_valid:
            # captcha was valid... carry on..nothing to see here
            pass
        else:
            _message = _('Wrong image verification code. Please try again.')
            self.add_message(_message, 'error')
            return self.redirect_to('password-reset')
        
        # load the email address
        email = str(self.request.POST.get('email')).lower().strip()
        if utils.is_email_valid(email):
            user = models.User.get_by_email(email)
            _message = _("You should receive an email from us shortly with instructions for resetting your password.")

        if user is not None:
            user_id = user.get_id()
            token = models.User.create_auth_token(user_id)
            email_url = self.uri_for('taskqueue-send-email')
            reset_url = self.uri_for('password-reset-check', user_id=user_id, token=token, _full=True)
            subject = _("%s Password Assistance" % config.app_name)

            # load email's template
            template_val = {
                "username": user.username,
                "email": user.email,
                "reset_password_url": reset_url,
                "support_url": self.uri_for("contact", _full=True),
                "app_name": config.app_name,
            }

            body_path = "emails/reset_password.txt"
            body = self.jinja2.render_template(body_path, **template_val)
            taskqueue.add(url = email_url, params={
                'to': user.email,
                'subject' : subject,
                'body' : body,
                'sender' : config.contact_sender,
                })
            self.add_message(_message, 'success')
            return self.redirect_to('login')

        self.add_message(_message, 'warning')
        return self.redirect_to('password-reset')

    @webapp2.cached_property
    def form(self):
        return forms.PasswordResetForm(self)


class PasswordResetCompleteHandler(BaseHandler):
    """
    Handler to process the link of reset password that received the user
    """

    def get(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        params = {}
        if verify[0] is None:
            message = _('The URL you tried to use is either incorrect or no longer valid. '
                        'Enter your details again below to get a new one.')
            self.add_message(message, 'warning')
            return self.redirect_to('password-reset')

        else:
            return self.render_template('user/password_reset_complete.html', **params)

    def post(self, user_id, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        user = verify[0]
        password = self.form.password.data.strip()
        if user and self.form.validate():
            # Password to SHA512
            password = utils.encrypt(password, config.salt)

            user.password = security.generate_password_hash(password, length=12)
            user.put()
            # Delete token
            models.User.delete_auth_token(int(user_id), token)
            # Login User
            self.auth.get_user_by_password(user.auth_ids[0], password)
            self.add_message(_('Password changed successfully.'), 'success')
            return self.redirect_to('home')

        else:
            self.add_message(_('The two passwords must match.'), 'error')
            return self.redirect_to('password-reset-check', user_id=user_id, token=token)

    @webapp2.cached_property
    def form(self):
        if self.is_mobile:
            return forms.PasswordResetCompleteMobileForm(self)
        else:
            return forms.PasswordResetCompleteForm(self)


class EmailChangedCompleteHandler(BaseHandler):
    """
    Handler for completed email change
    Will be called when the user click confirmation link from email
    """

    def get(self, user_id, encoded_email, token):
        verify = models.User.get_by_auth_token(int(user_id), token)
        email = utils.decode(encoded_email)
        if verify[0] is None:
            message = _('The URL you tried to use is either incorrect or no longer valid.')
            self.add_message(message, 'warning')
            self.redirect_to('home')

        else:
            # save new email
            user = verify[0]
            user.email = email
            user.put()
            # delete token
            models.User.delete_auth_token(int(user_id), token)
            # add successful message and redirect
            message = _('Your email has been successfully updated.')
            self.add_message(message, 'success')
            self.redirect_to('edit-profile')


class SecureRequestHandler(BaseHandler):
    """
    Only accessible to users that are logged in
    """

    @user_required
    def get(self, **kwargs):
        user_session = self.user
        user_session_object = self.auth.store.get_session(self.request)

        user_info = models.User.get_by_id(long( self.user_id ))
        user_info_object = self.auth.store.user_model.get_by_auth_token(
            user_session['user_id'], user_session['token'])

        try:
            params = {
                "user_session" : user_session,
                "user_session_object" : user_session_object,
                "user_info" : user_info,
                "user_info_object" : user_info_object,
                "userinfo_logout-url" : self.auth_config['logout_url'],
                }
            return self.render_template('secure_zone.html', **params)
        except (AttributeError, KeyError), e:
            return "Secure zone error:" + " %s." % e


class HomeRequestHandler(RegisterBaseHandler):
    """
    Handler to show the home page
    """

    def get(self):
        """ Returns a simple HTML form for home """
        params = {}
        return self.render_template('home.html', **params)


class ShellHandler(BaseHandler):
    @user_required
    def get(self):
        logging.info("foo")
        if (self.user):
            params = {'username': self.user}
            return self.render_template('shell.html', **params)
        else:
            self.redirect_to('login')

    def post(self):
        self.get()


class AppDetailHandler(BaseHandler):
    @user_required
    def get(self, app_id = None):
        params = {}
        return self.render_template('app/app_detail.html', **params)
    
    @webapp2.cached_property
    def form(self):
        return forms.AppForm(self)


class AppListHandler(BaseHandler):
    @user_required
    def get(self):
        params = {}
        return self.render_template('app/app_list.html', **params)
    # we'll need to pull gists from the user's github account to filter and list them
    # the idea is to re-log them into github if our token is expired and get a new one!

class AppCreateHandler(BaseHandler):
    @user_required
    def get(self):
        params = {}
        return self.render_template('app/app_create.html', **params)
        
    @user_required
    def post(self):
        user_info = models.User.get_by_id(long(self.user_id))
        if not app_id:
            appname = self.form.appname.data.strip()
            appurl = self.form.appurl.data.strip()
        
            app = models.App(
                appname = appname,
                appurl = appurl,
                created_by = user_info.key,
            )

            app.put()
            logging.info(app)
            self.add_message(_('App created.'), 'success')
            return self.redirect_to('app-detail', )
        else:
            pass

    @webapp2.cached_property
    def form(self):
        return forms.AppForm(self)


class ProductHandler(BaseHandler):
    def get(self, product_page=''):
        params = {"product_page": product_page}

        if product_page == 'pricing':
            return self.render_template('product/pricing.html', **params)
        else:
            return self.render_template('home.html', **params)


class CompanyHandler(BaseHandler):
    def get(self, product_page=''):
        params = {"company_page": company_page}
        if company_page == 'pricing':
            return self.render_template('company/pricing.html', **params)
        else:
            return self.render_template('home.html', **params)








