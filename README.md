# StackGeek Website in a Box
This is the production code running on http://stackgeek.com/.  

StackGeek provides a community contributed blog for discussing infrastructure architecture, managment and monitoring.  The site and posts are 100% Open Source.  Posts are stored as Gists in user's accounts, and can be forked in a similar way you fork and modify source code.

## Google AppEngine Boilerplate
The site is built using the GAEB project hosted on Github: http://github.com/gae-boilerplate.  Any modifications made to the StackGeek site which are core to the project should be submitted to GAEB directly for pull requests.

##Blogging with the Code
Blog posts on StackGeek are stored as Gists in your Github account.  The site (GAEB) supports Github social integration, so you can tie your account to Github and have the site create gists which are the truth for blog posts and guides on the site.  These gist articles are stored entirely in your Github account and are, of course, 100% your copyrighted content. 

StackGeek will keep track of the posts you keep in your Gists, and cache them locally in memcache for rapid serving of content when your articles are viewed.  If you make edits to your articles, you can tell StackGeek to clear the cache and refetch the article content from your Github account.

##More to come...