from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^insanity/', include('web.insanity.urls')),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
)
