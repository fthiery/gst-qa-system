import os.path
from django import template
from django.utils.html import escape

register = template.Library()

@register.tag
def test_arg_value(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        func, arg_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one arguments" % token.contents.split()[0]

    return TestArgValueNode(arg_name)

@register.simple_tag
def verticalize(toparse):
    return "<br>".join([a[0].capitalize() for a in toparse.split('-')])

@register.simple_tag
def split_dash_lines(toparse):
    return "<br>".join([a.capitalize() for a in toparse.split('-')])

@register.tag
def test_extrainfo_value(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        func, value_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one arguments" % token.contents.split()[0]

    return TestExtraInfoValueNode(value_name)

# common methods
def escape_val(val, safe=False):
    if isinstance(val, list) or isinstance(val, tuple):
        res = ["<ul>"]
        for item in val:
            res.extend(["<li>", escape_val(item, safe), "</li>"])
        res.append("</ul>")
        return "".join(res)
    if isinstance(val, dict):
        res = ["<dl>"]
        for k,v in val.iteritems():
            res.extend(["<dt>", escape_val(k, safe), "</dt>"])
            res.extend(["<dd>", escape_val(v, safe), "</dd>"])
        res.append("</dl>")
        return "".join(res)
    if safe:
        return unicode(val)
    return escape(unicode(val))


class TestArgValueNode(template.Node):

    def __init__(self, arg):
        self._arg_name = arg

    def render(self, context):
        # render based on the type
        arg = context[self._arg_name]
        # insert custom arg value handling here
        return arg.value

class TestExtraInfoValueNode(template.Node):

    def __init__(self, extrainfo):
        self._extrainfo_name = extrainfo

    def render(self, context):
        floatsecondtypes = ["test-total-duration",
                            "test-setup-duration",
                            "remote-instance-creation-delay",
                            "subprocess-spawn-time"]
        gstsecondtypes = ["first-buffer-timestamp",
                          "total-uri-duration"]


        def elements_used_dict(elements):
            # returns a dictionnary of the tree of elements used
            def insert_in_dict(d,el,par,klass):
                if d == {}:
                    d[el] = [klass, {}]
                    return True
                for k in d.iterkeys():
                    if k == par:
                        d[k][1][el] = [klass, {}]
                        return True
                    if d[k][1] != {}:
                        if insert_in_dict(d[k][1], el, par, klass):
                            return True
                return False
            def switch_dict(d):
                res = {}
                for k,v in d.iteritems():
                    klass, childs = v
                    res["<b>%s</b> (type:%s)" % (k, klass)] = switch_dict(childs)
                return res
            d = {}
            for el, klass, container in elements:
                insert_in_dict(d, el, container, klass)

            return switch_dict(d)

        def time_to_string(value):
            if value == -1.0:
                return "--:--:--.---"
            ms = value / 1000000
            sec = ms / 1000
            ms = ms % 1000
            mins = sec / 60
            sec = sec % 60
            hours = mins / 60
            return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

        def newsegment_tuple(tup):
            update,rate,format,start,stop,pos = tup
            return "<br>".join(["Update : %d" % update,
                                "Rate : %f" % rate,
                                "GstFormat : %d" % format,
                                "start : %s" % time_to_string(start),
                                "stop : %s" % time_to_string(stop),
                                "pos : %s" % time_to_string(pos)])

        # render based on the type
        extrainfo = context[self._extrainfo_name]
        # insert custom extrainfo value handling here
        if extrainfo.name.name in gstsecondtypes:
            res = time_to_string(extrainfo.value)
        elif extrainfo.name.name in floatsecondtypes:
            res = time_to_string(float(extrainfo.value) * 1000000000)
        elif extrainfo.name.name == "elements-used":
            res = escape_val(elements_used_dict(extrainfo.value), safe=True)
        elif extrainfo.name.name == "newsegment-values":
            res = newsegment_tuple(extrainfo.value)
        else:
            res = escape_val(extrainfo.value)
        return res

@register.inclusion_tag('insanity/test_args_dict.html')
def test_args_dict(test, fullarguments=None):
    args = test.arguments.all().select_related(depth=1)
    return {'args':args}


@register.inclusion_tag('insanity/test_checklist_dict.html')
def test_checklist_dict(test, fullchecklist=None):
    results = test._get_results_dict(fullchecklist)
    return {'results':results}

@register.inclusion_tag('insanity/test_extrainfo_dict.html')
def test_extrainfo_dict(test):
    extrainfos = test.extrainfo.all().select_related(depth=1)
    return {'extrainfos':extrainfos}

@register.inclusion_tag('insanity/matrix_checklist_row.html')
def matrix_checklist_row(test, fullchecklist, fullarguments,
                         allchecks, allargs, allextrainfo):
    arguments = test._get_full_arguments(fullarguments, allargs)
    results = test._get_results_dict(fullchecklist, allchecks)
    test_error = test._test_error(allextras=allextrainfo)
    return {'test':test,
            'arguments':arguments,
            'results':results,
            'test_error':test_error}

