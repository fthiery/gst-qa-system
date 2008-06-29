from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:
    # (r'^webview/', include('webview.foo.urls')),
    (r'^insanity/', include('web.insanity.urls')),

    # Uncomment this for admin:
     (r'^admin/', include('django.contrib.admin.urls')),
)
