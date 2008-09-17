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

@register.tag
def test_extrainfo_value(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        func, value_name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires exactly one arguments" % token.contents.split()[0]

    return TestExtraInfoValueNode(value_name)

# common methods
def escape_val(val):
    if isinstance(val, str):
        return escape(val)
    elif isinstance(val, list) or isinstance(val, tuple):
        res = ["<ul>"]
        for item in val:
            res.extend(["<li>", escape_val(item), "</li>"])
        res.append("</ul>")
        return "".join(res)
    elif isinstance(val, dict):
        res = ["<dl>"]
        for k,v in val.iteritems():
            res.extend(["<dt>", escape_val(k), "</dt>"])
            res.extend(["<dd>", escape_val(v), "</dd>"])
        res.append("</dl>")
        return "".join(res)
    return escape(str(val))


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
        gstsecondtypes = ["test-total-duration",
                          "test-setup-duration",
                          "remote-instance-creation-delay",
                          "subprocess-spawn-time"]


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
                    res["%s (type:%s)" % (k, klass)] = switch_dict(childs)
                return res
            d = {}
            for el, klass, container in elements:
                insert_in_dict(d, el, container, klass)

            return switch_dict(d)

        def time_to_string(value):
            value = float(value) * 1000000000
            if value == -1:
                return "--:--:--.---"
            ms = value / 1000000
            sec = ms / 1000
            ms = ms % 1000
            mins = sec / 60
            sec = sec % 60
            hours = mins / 60
            return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

        # render based on the type
        extrainfo = context[self._extrainfo_name]
        # insert custom extrainfo value handling here
        if extrainfo.name.name in gstsecondtypes:
            res = time_to_string(extrainfo.value)
        elif extrainfo.name.name == "elements-used":
            res = escape_val(elements_used_dict(extrainfo.value))
        else:
            res = escape_val(extrainfo.value)
        return res

@register.inclusion_tag('insanity/test_args_dict.html')
def test_args_dict(test):
    args = test.arguments.all()
    return {'args':args}


@register.inclusion_tag('insanity/test_checklist_dict.html')
def test_checklist_dict(test):
    checks = test.checklist.all()
    return {'checks':checks}

@register.inclusion_tag('insanity/test_extrainfo_dict.html')
def test_extrainfo_dict(test):
    extrainfos = test.extrainfo.all()
    return {'extrainfos':extrainfos}

