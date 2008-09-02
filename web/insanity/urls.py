from django.conf.urls.defaults import *

urlpatterns = patterns('web.insanity.views',
                       (r'^$', 'index'),
                       (r'^testrun/(?P<testrun_id>\d+)/$', 'testrun_summary'),
                       (r'^test/(?P<test_id>\d+)/$', 'test_summary'),
                       (r'^matrix/(?P<testrun_id>\d+)/$', 'matrix_view'),
                       (r'^available_tests/$', 'available_tests')
#     (r'^(?P<poll_id>\d+)/$', 'detail'),
#     (r'^(?P<poll_id>\d+)/results/$', 'results'),
#     (r'^(?P<poll_id>\d+)/vote/$', 'vote'),
)
