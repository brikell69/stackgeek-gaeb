#!/usr/bin/env python
##
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

__author__ = 'Kord Campbell'
__website__ = 'http://www.tinyprobe.com'

import config
import urllib, httplib2, simplejson, yaml
import lib.github.oauth_client as oauth2
from google.appengine.api import memcache
import logging

# mark up, down, left, right
from lib.markdown import markdown
from lib.docutils.core import publish_parts

# Github OAuth Implementation
class GithubAuth(object):
    
    def __init__(self, scope, next_page=''):

        # load github shizzle from config.py
        self.oauth_settings = {
            'client_id': config.github_client_id,
            'client_secret': config.github_client_secret,
            'access_token_url': 'https://%s/login/oauth/access_token' % config.github_server,
            'authorization_url': 'https://%s/login/oauth/authorize' % config.github_server,
            'redirect_url': '%s' % config.github_redirect_uri,
            'scope': '%s' % scope,
        }

    # get our auth url and return to login handler
    def get_authorize_url(self):
        oauth_client = oauth2.Client2( 
            self.oauth_settings['client_id'], 
            self.oauth_settings['client_secret'], 
            self.oauth_settings['authorization_url'] 
        )
        
        authorization_url = oauth_client.authorization_url( 
            redirect_uri=self.oauth_settings['redirect_url'],  
            params={'scope': self.oauth_settings['scope']}
        )

        return authorization_url

    def get_access_token(self, code):
        oauth_client = oauth2.Client2(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )
        
        data = oauth_client.access_token(code, self.oauth_settings['redirect_url'])
        
        access_token = data.get('access_token')

        return access_token


    def get_user_info(self, access_token):

        oauth_client = oauth2.Client2(
            self.oauth_settings['client_id'],
            self.oauth_settings['client_secret'],
            self.oauth_settings['access_token_url']
        )

        (headers, body) = oauth_client.request(
            'https://api.github.com/user',
            access_token=access_token,
            token_param='access_token'
        )
        
        return simplejson.loads(body)


def get_user_gists(github_user, access_token):
    params = {'access_token': access_token}
    base_uri = 'https://api.github.com/users/%s/gists' % github_user
    uri = '%s?%s' % (base_uri, urllib.urlencode(params))
    
    try:
        # request data from github gist API
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='GET', body=None, headers=None)
        gists = simplejson.loads(content)

        # transform gists into articles
        articles = []
        for gist in gists:
            try:
                # grab the raw file and parse it for yaml bits
                if gist['files'][config.gist_manifest_name]['raw_url']:
                    headers, content = http.request(gist['files'][config.gist_manifest_name]['raw_url'])
                    manifest = yaml.load(content)

                # stuff it onto article list
                articles.append({
                    'title': manifest['title'], 
                    'summary': manifest['summary'], 
                    'published': manifest['published'],
                    'article_type': manifest['type'],
                    'gist_id': gist['id'],
                })
            
            except:
                # gist didn't have a .manifest file - so sad
                pass

        return articles

    except:
        pass
        # TODO do somthing if getting the gists fails


# fetch either .md or .rst files from github and render into html, caching as needed
def get_gist_content(gist_id):
    content = memcache.get('%s:content' % gist_id)
    if content is not None:
        return content
    else:
        logging.info("cache miss for %s" % gist_id)
        Try:
            # go fetch the gist using the gist_id
            http = httplib2.Http(cache=None, timeout=10, proxy_info=None)
            headers, content = http.request('https://api.github.com/gists/%s' % gist_id, method='GET', body=None, headers=None)
            
            if headers['status'] == '404':
                logging.info("looked for gist ID %s but didn't find it.  404 bitches.")
                return False

            # strip bad UTF-8 stuff if it exists (like in a gist with a .png)
            content = content.decode('utf-8', 'replace')
            gist = simplejson.loads(content)

            # see if we have .md or .rst file matching our filenames in config
            if config.gist_markdown_name in gist['files']:
                gist_content_url = gist['files'][config.gist_markdown_name]['raw_url']
                headers, content = http.request(gist_content_url, method='GET', headers=None)
                gist_html = markdown.markdown(content)
            elif config.gist_restructuredtext_name in gist['files']:
                gist_content_url = gist['files'][config.gist_restructuredtext_name]['raw_url']
                headers, content = http.request(gist_content_url, method='GET', headers=None)
                parts = publish_parts(source=content, writer_name='html4css1', settings_overrides={'title': '', 'report_level': 'quiet', '_disable_config': True})
                gist_html = parts['html_body'].replace('class="docinfo"', 'class="table table-striped"').replace('class="docutils', 'class="table table-striped table-bordered')
            else:
                logging.info("not finding a valid markdown file to display for content")
                return False
            
            if not memcache.add('%s:content' % gist_id, gist_html, config.memcache_expire_time):
                logging.info("memcache add of content from gist %s failed." % gist_id)

            return gist_html

        except:
            logging.info("got an exception while talking to github")
            return False

def fork_gist(access_token, gist_id):
    try:
        params = {'access_token': access_token}
        uri = 'https://api.github.com/gists/%s/fork?%s' % (gist_id, urllib.urlencode(params))
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='POST', headers=None)
        gist = simplejson.loads(content)

        try:
            # grab the raw file and parse it for yaml bits
            if gist['files'][config.gist_manifest_name]['raw_url']:
                headers, content = http.request(gist['files'][config.gist_manifest_name]['raw_url'])
                manifest = yaml.load(content)
        
            gist_meta = {
                'title': manifest['title'], 
                'summary': manifest['summary'], 
                'published': manifest['published'],
                'article_type': manifest['type'],
                'gist_id': gist['id'],
            }

            return gist_meta

        except:
            return False 

    except:
        logging.info("%s was not forked because %s" % (gist_id, content))
        return False


def flush_gist_content(gist_id):
    if memcache.delete('%s:content' % gist_id):
        logging.info("flushed cache!")
        return True
    else:
        logging.info("didn't flush cache!")
        return False


def put_user_gist(access_token, body):
    try:
        # stuff that sucker to github
        params = {'access_token': access_token}
        base_uri = 'https://api.github.com/gists'
        uri = '%s?%s' % (base_uri, urllib.urlencode(params))
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='POST', body=body, headers=None)

        # check github said it made it ok
        return simplejson.loads(content)
    except:
        return False


def delete_user_gist(access_token, gist_id):
    try:
        # stuff that sucker to github
        params = {'access_token': access_token}
        base_uri = 'https://api.github.com/gists/%s' % gist_id
        uri = '%s?%s' % (base_uri, urllib.urlencode(params))
        http = httplib2.Http(cache=None, timeout=None, proxy_info=None)
        headers, content = http.request(uri, method='DELETE', headers=None)        
    except:
        return False
