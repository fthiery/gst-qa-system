from django.conf.urls.defaults import *
from django import VERSION

if VERSION >= (1, 0, ''):
    from django.contrib import admin
    admin.autodiscover()
    urlpatterns = patterns('',
                           (r'^insanity/', include('web.insanity.urls')),
                           (r'^admin/', admin.site.root))
else:
    urlpatterns = patterns('',
                           (r'^insanity/', include('web.insanity.urls')),
                           (r'^admin/', include('django.contrib.admin.urls')))
