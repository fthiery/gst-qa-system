from web.insanity.models import TestRun
from django.http import HttpResponse
import time

def index(request):
    latest_runs = TestRun.objects.all()[:5]
    output = ", ".join([str(r) for r in latest_runs])
    return HttpResponse(output)

