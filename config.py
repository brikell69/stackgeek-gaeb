import os, logging

# application details
app_name = "xxxxxxxxxxxxxxxx"
site_bio = "A site for xxxxxxxxxxxxxxxx nuts.  And xxxxxxxxxxxxxxxx."

# template configuration
webapp2_config = {}
webapp2_config['webapp2_extras.sessions'] = {
    'secret_key': 'xxxxxxxxxxxxxxxx',
}
webapp2_config['webapp2_extras.auth'] = {
    'user_model': 'web.models.models.User',
    'cookie_name': 'session_name'
}
webapp2_config['webapp2_extras.jinja2'] = {
    'template_path': 'templates',
    'environment_args': {'extensions': ['jinja2.ext.i18n']},
}

# Enable Federated login (OpenID and OAuth)
# Google App Engine Settings must be set to Authentication Options: Federated Login
enable_federated_login = True

# jinja2 base layout templates
base_layout = 'base.html'

# show some mistakes
error_templates = {
    403: 'errors/default_error.html',
    404: 'errors/default_error.html',
    500: 'errors/default_error.html',
}

# html whitelist for bleached articles
bleach_tags = ['p', 'em', 'strong', 'code', 'h1', 'h2', 'h3', 'h4', 'h5', 'td', 'li', 'ul', 'ol', 'table', 'tbody', 'thead', 'iframe', 'tr', 'th', 'span',  'pre', 'i', 'button', 'img', 'a']
bleach_attributes = {'i': ['class'], 'a': ['href', 'rel'], 'table': ['class'], 'img': ['src', 'alt'], 'iframe': ['src', 'width', 'height', 'frameborder'], 'pre': ['class']}

# locale settings
app_lang = 'en'
locales = ['en_US']

# send mail as (has to be google appengine admin account)
contact_sender = "user@example.com"
contact_recipient = "user@example.com"

# Password AES Encryption Parameters
aes_key = "xxxxxxxxxxxxxxxx"
salt = "xxxxxxxxxxxxxxxx"

# issue a job token to prevent others from running our tasks by knowing URL
job_token = 'xxxxxxxxxxxxxxxx'

# get your own consumer key and consumer secret by registering at https://dev.twitter.com/apps
# callback url must be: http://[YOUR DOMAIN]/login/twitter/complete
twitter_consumer_key = 'xxxxxxxxxxxxxxxx'
twitter_consumer_secret = 'xxxxxxxxxxxxxxxx'

# github app handling - available under admin..applications on Github
if os.environ['SERVER_SOFTWARE'].startswith('Dev'):
  # github login for TinyProbe dev
	github_server = 'github.com'
	github_redirect_uri = 'http://localhost:8105/social_login/github/complete'
	github_client_id = 'xxxxxxxxxxxxxxxx'
	github_client_secret = 'xxxxxxxxxxxxxxxx'
else:
	# going production level
	github_server = 'github.com'
	github_redirect_uri = 'http://xxxxxxxxxxxxxxxx.appspot.com/social_login/github/complete'
	github_client_id = 'xxxxxxxxxxxxxxxx'
	github_client_secret = 'xxxxxxxxxxxxxxxx'

# gist memcache settings
gist_manifest_name = 'stackgeek.manifest'
gist_markdown_name = 'stackgeek.md'
memcache_expire_time = 604800

# gravatar holder image
gravatar_url_stub = "http://s.gravatar.com/avatar/xxxxxxxxxxxxxxxx"

# get your own recaptcha keys by registering at www.google.com/recaptcha
captcha_public_key = "xxxxxxxxxxxxxxxx"
captcha_private_key = "xxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx"

# tracking shizzle
google_analytics_code = "UA-xxxxxxxxxxxxxxxx-1"



