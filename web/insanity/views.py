from web.insanity.models import TestRun, Test, TestClassInfo
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse
import time

def index(request):
    nbruns = request.GET.get("nbruns", 20)
    latest_runs = TestRun.objects.all()[:int(nbruns)]
    return render_to_response("insanity/index.html", {"latest_runs":latest_runs,
                                                      "nbruns":nbruns})

def testrun_summary(request, testrun_id):
    toplevel_only = bool(int(request.GET.get("toplevel",True)))
    tr = get_object_or_404(TestRun, pk=testrun_id)
    return render_to_response('insanity/testrun_summary.html',
                              {'testrun': tr,
                               'toplevel_only': toplevel_only})

def test_summary(request, test_id):
    tr = get_object_or_404(Test, pk=test_id)
    return render_to_response('insanity/test_summary.html', {'test': tr})

def available_tests(request):
    """ Returns a tree of all available tests """
    classinfos = TestClassInfo.objects.all()
    return render_to_response('insanity/available_tests.html',
                              {"classinfos": classinfos})

def matrix_view(request, testrun_id):
    tr = get_object_or_404(TestRun, pk=testrun_id)
    onlyfailed = bool(int(request.GET.get("onlyfailed",False)))
    showscenario = bool(int(request.GET.get("showscenario",True)))
    limit = int(request.GET.get("limit", -1))
    offset = int(request.GET.get("offset", 0))
    # following returns a list of {"type" : testtypeid}
    testtypesid = tr.test_set.values("type").distinct()
    tests = []
    for d in testtypesid:
        t = TestClassInfo.objects.get(pk=d["type"])
        if not showscenario and t.is_scenario:
            continue
        query = Test.objects.filter(testrunid=int(testrun_id),
                                    type=t)
        if limit != -1:
            query = query[offset:offset+limit]
        # FIXME : find a way to filter out successful tests if onlyfailed
        tests.append({"type":t,
                      "tests":query})
    return render_to_response('insanity/matrix_view.html',
                              {'testrun':tr,
                               'sortedtests':tests,
                               'onlyfailed':onlyfailed})

def handler404(request):
    return "Something went wrong !"
