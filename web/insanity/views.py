from web.insanity.models import TestRun, Test
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
import time

def index(request):
    nbruns = request.GET.get("nbruns", 5)
    latest_runs = TestRun.objects.all()[:int(nbruns)]
    return render_to_response("insanity/index.html", {"latest_runs":latest_runs})

def testrun_summary(request, testrun_id):
    toplevel_only = bool(int(request.GET.get("toplevel",True)))
    tr = get_object_or_404(TestRun, pk=testrun_id)
    return render_to_response('insanity/testrun_summary.html',
                              {'testrun': tr,
                               'toplevel_only': toplevel_only})

def test_summary(request, test_id):
    tr = get_object_or_404(Test, pk=test_id)
    return render_to_response('insanity/test_summary.html', {'test': tr})

def handler404(request):
    return "Something went wrong !"
