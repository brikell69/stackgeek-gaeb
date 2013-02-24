"""
Using redirect route instead of simple routes since it supports strict_slash
Simple route: http://webapp-improved.appspot.com/guide/routing.html#simple-routes
RedirectRoute: http://webapp-improved.appspot.com/api/webapp2_extras/routes.html#webapp2_extras.routes.RedirectRoute
"""

from webapp2_extras.routes import RedirectRoute
from web import handlers
from web.users import userhandlers
from web.blog import bloghandlers

secure_scheme = 'https'

_routes = [
    # redirects - don't delete
    RedirectRoute('/company/index.html', redirect_to_name='about'),
    RedirectRoute('/blog/index.html', redirect_to_name='blog'),
    RedirectRoute('/guides/index.html', redirect_to_name='guides'),
    RedirectRoute('/blog/archive.html', redirect_to_name='blog'),

    # our breadwinner - don't delete
    RedirectRoute('/blog/kordless/guides/gettingstarted.html', redirect_to_name='guides-article', defaults={'slug': 'gettingstarted.html'}),
    RedirectRoute('/blog/kordless/guide/gettingstarted.html', redirect_to_name='guides-article', defaults={'slug': 'gettingstarted.html'}),

    # redirects for a bad slug we had - remove 1/1/13
    RedirectRoute('/blog/kordless/posts/increase-the-size-of-devstack-s-volumes', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'increase-the-size-of-devstacks-volumes'}),
    RedirectRoute('/blog/kordless/post/increase-the-size-of-devstack-s-volumes', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'increase-the-size-of-devstacks-volumes'}),
    RedirectRoute('/blog/archives/2012-1/02', redirect_to_name='blog'),

    # old format for blog posts - leave in place
    RedirectRoute('/2012/02/21/taking-openstack-for-a-spin/', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'taking-openstack-for-a-spin'}),
    RedirectRoute('/2012/04/28/increase-the-size-of-devstacks-volumes/', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'increase-the-size-of-devstacks-volumes'}),
    RedirectRoute('/2012/04/28/increase-the-size-devstacks-cloud-volumes/', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'increase-the-size-of-devstacks-volumes'}),
    RedirectRoute('/2012/04/08/open-source-private-cloud-support/', redirect_to_name='blog-article-slug', defaults={'username': 'kordless', 'article_type': 'post', 'slug': 'comparison-of-open-source-cloud-support-for-ec2'}),

    # mail processing
    RedirectRoute('/taskqueue-send-email/', handlers.SendEmailHandler, name='taskqueue-send-email', strict_slash=True),

    # user logins
    RedirectRoute('/login/', userhandlers.LoginHandler, name='login', strict_slash=True),
    RedirectRoute('/logout/', userhandlers.LogoutHandler, name='logout', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>', userhandlers.SocialLoginHandler, name='social-login', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>/complete', userhandlers.CallbackSocialLoginHandler, name='social-login-complete', strict_slash=True),
    RedirectRoute('/social_login/<provider_name>/delete', userhandlers.DeleteSocialProviderHandler, name='delete-social-provider', strict_slash=True),

    # user registration
    RedirectRoute('/preregister/', userhandlers.PreRegisterHandler, name='preregister', strict_slash=True),
    RedirectRoute('/register/<encoded_email>/', userhandlers.RegisterHandler, name='register', strict_slash=True),

    # user settings
    RedirectRoute('/settings/profile', userhandlers.EditProfileHandler, name='edit-profile', strict_slash=True),
    RedirectRoute('/settings/password', userhandlers.EditPasswordHandler, name='edit-password', strict_slash=True),
    RedirectRoute('/settings/email', userhandlers.EditEmailHandler, name='edit-email', strict_slash=True),
    RedirectRoute('/password-reset/', userhandlers.PasswordResetHandler, name='password-reset', strict_slash=True),
    RedirectRoute('/password-reset/<user_id>/<token>', userhandlers.PasswordResetCompleteHandler, name='password-reset-check', strict_slash=True),
    RedirectRoute('/change-email/<user_id>/<encoded_email>/<token>/', userhandlers.EmailChangedCompleteHandler, name='email-changed-check', strict_slash=True),
    RedirectRoute('/secure/', userhandlers.SecureRequestHandler, name='secure', strict_slash=True),

    # website pages
    RedirectRoute('/', handlers.HomeRequestHandler, name='home', strict_slash=True),
    RedirectRoute('/forums/', handlers.ForumsHandler, name='forums', strict_slash=True),
    RedirectRoute('/videos/', handlers.VideosHandler, name='videos', strict_slash=True),
    RedirectRoute('/about/', handlers.AboutHandler, name='about', strict_slash=True),
    RedirectRoute('/terms/', handlers.TermsHandler, name='terms', strict_slash=True),
    RedirectRoute('/contact/', handlers.ContactHandler, name='contact', strict_slash=True),

    # blog handlers
    RedirectRoute('/blog/', bloghandlers.PublicBlogHandler, name='blog', strict_slash=True),
    RedirectRoute('/blog/feed/rss/', bloghandlers.PublicBlogRSSHandler, name='blog-rss', strict_slash=True),
    RedirectRoute('/blog/refresh/', bloghandlers.BlogRefreshHandler, name='blog-refresh', strict_slash=True),
    RedirectRoute('/blog/buildlist/', bloghandlers.BlogBuildListHandler, name='blog-build', strict_slash=True),
    RedirectRoute('/blog/menu/<menu_id>', bloghandlers.BlogUserMenuHandler, name='blog-menu', strict_slash=True), # see class for fix info
    RedirectRoute('/blog/<username>/new/', bloghandlers.BlogArticleCreateHandler, name='blog-article-create', strict_slash=True),
    RedirectRoute('/blog/<username>/articles/', bloghandlers.BlogArticleListHandler, name='blog-article-list', strict_slash=True),
    RedirectRoute('/blog/<username>/<article_id>/refresh/', bloghandlers.BlogClearCacheHandler, name='blog-clearcache', strict_slash=True),
    RedirectRoute('/blog/<username>/<article_type>/<slug>', bloghandlers.BlogArticleSlugHandler, name='blog-article-slug', strict_slash=True),
    RedirectRoute('/blog/<username>/<article_id>/', bloghandlers.BlogArticleActionsHandler, name='blog-article-actions', strict_slash=True),
    RedirectRoute('/blog/<username>/', bloghandlers.BlogUserHandler, name='blog-user', strict_slash=True),
    RedirectRoute('/guides/', bloghandlers.PublicGuideHandler, name='guides', strict_slash=True),

    # throwback URLs for old stackgeek.com site - do not include in gae-boilerplate changes
    RedirectRoute('/guides/<slug>', bloghandlers.BlogArticleSlugHandler, name='guides-article', strict_slash=True),

    # channel watcher
    RedirectRoute('/_ah/channel/connected/', handlers.channelHandler, name='channel-connected', strict_slash=True),
    RedirectRoute('/_ah/channel/disconnected/', handlers.channelHandler, name='channel-disconnected', strict_slash=True),
    RedirectRoute('/_ah/channel/dev', handlers.channelHandler, name='channel-dev', strict_slash=True),
    RedirectRoute('/_ah/warmup', handlers.warmupHandler, name='channel-dev', strict_slash=True),
]

def get_routes():
    return _routes

def add_routes(app):
    if app.debug:
        secure_scheme = 'http'
    for r in _routes:
        app.router.add(r)
