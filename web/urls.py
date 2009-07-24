from django.conf.urls.defaults import *
from django import VERSION
from django.conf import settings
import os

from django.contrib import admin
admin.autodiscover()
urlpatterns = patterns('',
                           (r'^insanity/', include('web.insanity.urls')),
                           (r'^admin/', admin.site.root))
if settings.DEBUG:
    # This is temporary
    # DO NOT USE IN PRODUCTION. See django documentation about serving
    # static files

    # in the meantime... we take ../site_media/
    docroot = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_media')
    urlpatterns += patterns('',
        (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': docroot}),
    )
