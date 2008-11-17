import time
import string
import datetime
import os.path
from cPickle import dumps, loads
from django.db import models
from django.db.models import permalink
from django.db import connection

class DateTimeIntegerField(models.DateTimeField):

    """Like DateTimeField, but reads the value from an integer UNIX timestamp."""

    __metaclass__ = models.SubfieldBase

    def to_python(self, value):
        if isinstance(value, int) or isinstance(value, long):
            value = datetime.datetime.fromtimestamp(value)
        return models.DateTimeField.to_python(self, value)

class CustomSQLInterface:

    def _fetchAll(self, instruction, *args, **kwargs):
        cur = connection.cursor()
        cur.execute(instruction, *args, **kwargs)
        res = cur.fetchall()
        return res

    def _fetchOne(self, instruction, *args, **kwargs):
        cur = connection.cursor()
        cur.execute(instruction, *args, **kwargs)
        res = cur.fetchone()
        return res

class Client(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    software = models.TextField(blank=True)
    name = models.TextField(blank=True)
    user = models.TextField(blank=True)
    class Meta:
        db_table = 'client'

    class Admin:
        pass

    def __str__(self):
        return "Client #%d [%s/%s/%s]" % (self.id, self.software, self.name,
                                          self.user)

class MonitorClassInfo(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    type = models.TextField(blank=True)
    parent = models.ForeignKey("self", db_column="parent",
                               related_name="subclass")
    description = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo'

class MonitorClassInfoArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid",
                                    related_name="argument")
    name = models.TextField(blank=True)
    value = models.TextField(blank=True,
                             db_column="txtvalue")
    class Meta:
        db_table = 'monitorclassinfo_arguments_dict'

class MonitorClassInfoCheckListDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid",
                                    related_name="checklist")
    name = models.TextField(blank=True)
    value = models.TextField(blank=True,
                             db_column="txtvalue")
    class Meta:
        db_table = 'monitorclassinfo_checklist_dict'

class MonitorClassInfoExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid",
                                    related_name="extrainfo")
    name = models.TextField(blank=True)
    value = models.TextField(blank=True,
                             db_column="txtvalue")

    class Meta:
        db_table = 'monitorclassinfo_extrainfo_dict'

class MonitorClassInfoOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid",
                                    related_name="outputfiles")
    name = models.TextField(blank=True)
    value = models.TextField(blank=True,
                             db_column="txtvalue")
    class Meta:
        db_table = 'monitorclassinfo_outputfiles_dict'

class TestClassInfoManager(models.Manager):
    def scenarios(self):
        """Returns all scenario TestClasses"""
        sct = self.get(type="scenario")
        v = self.all().select_related("id", "type", "parent")
        def filter_subclass(ptype, avail):
            res = [ptype]
            for t in avail:
                if ptype == t.parent:
                    res.extend(filter_subclass(t, avail))
            return res

        return filter_subclass(sct, v)

class TestClassInfo(models.Model):
    objects = TestClassInfoManager()
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    type = models.TextField(blank=True)
    parent = models.ForeignKey("self", to_field="type",
                               db_column="parent",
                               related_name="subclass")
    description = models.TextField(blank=True)
    fulldescription = models.TextField(blank=True)

    def _get_fullchecklist(self):
        """
        Returns the full list of checkitems (including from parents)
        The list is ordered by classes and then by id.
        """
        # this should be done in two queries
        # 1. get the list of all testclassinfo (from here to base)
        # 2. get the checklist for all those classes
        if hasattr(self,"__cached_fullchecklist"):
            return self.__cached_fullchecklist
        classes = self.__get_parentage()
        res = TestClassInfoCheckListDict.objects.filter(containerid__in=classes)
        self.__cached_fullchecklist = res
        return res
    fullchecklist = property(_get_fullchecklist)

    def _get_fullarguments(self):
        """
        Returns the full list of arguments (including from parents).
        The list is ordered by classes and then by id.
        """
        classes = self.__get_parentage()
        res = TestClassInfoArgumentsDict.objects.filter(containerid__in=classes).select_related(depth=1)
        return res
    fullarguments = property(_get_fullarguments)

    def _get_is_scenario(self):
        if self.type == "scenario":
            return True
        if self.parent_id:
            return self.parent.is_scenario
        return False
    is_scenario = property(_get_is_scenario)

    def __get_parentage(self):
        if hasattr(self, "__cached_parentage"):
            return self.__cached_parentage
        res = [self.id]
        if self.parent_id:
            res.extend(self.parent.__get_parentage())
        self.__cached_parentage = res
        return res

    def __repr__(self):
        return "TestClassInfo:%s" % self.type

    class Meta:
        db_table = 'testclassinfo'

class TestClassInfoArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo,
                                    db_column="containerid",
                                    related_name="arguments")
    name = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        return loads(str(self.blobvalue))
    value = property(_get_value)

    def _get_description(self):
        return self.value[0]
    description = property(_get_description)

    def _get_defaultvalue(self):
        return self.value[1]
    defaultvalue = property(_get_defaultvalue)

    def _get_fulldescription(self):
        return self.value[2]
    fulldescription = property(_get_fulldescription)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'testclassinfo_arguments_dict'

class TestClassInfoCheckListDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo,
                                    db_column="containerid",
                                    related_name="checklist")
    name = models.TextField(blank=True)
    description = models.TextField(blank=True,
                                   db_column="txtvalue")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'testclassinfo_checklist_dict'

class TestClassInfoExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo,
                                    db_column="containerid",
                                    related_name="extrainfos")
    name = models.TextField(blank=True)
    description = models.TextField(blank=True, db_column="txtvalue")
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'testclassinfo_extrainfo_dict'

class TestClassInfoOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo,
                                    db_column="containerid",
                                    related_name="outputfiles")
    name = models.TextField(blank=True)
    value = models.TextField(blank=True, db_column="txtvalue")
    def __str__(self):
        return self.name

    class Meta:
        db_table = 'testclassinfo_outputfiles_dict'


class TestRunManager(models.Manager):
    def withcounts(self):
        return self.all().extra(select={'nbtests':"SELECT COUNT(*) FROM test WHERE test.testrunid = testrun.id"})

class TestRun(models.Model, CustomSQLInterface):
    objects = TestRunManager()
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    clientid = models.ForeignKey(Client, db_column="clientid")
    starttime = DateTimeIntegerField(null=True, blank=True)
    stoptime = DateTimeIntegerField(null=True, blank=True)
    class Meta:
        db_table = 'testrun'

    def get_absolute_url(self):
        return ('web.insanity.views.matrix_view', [str(self.id)])
    get_absolute_url = permalink(get_absolute_url)

    def get_matrix_view_url(self):
        return ('web.insanity.views.matrix_view', [self.id])
    get_matrix_view_url = permalink(get_matrix_view_url)

    def find_test_similar_args(self, atest):
        """Returns tests which have the similar arguments as atest"""
        # this query is too complex to do with DJango code
        # if somebody can convert it to django code, you're welcome
        # FIXME : This can be done in one SQL query
        res = [x.id for x in self.test_set.filter(type__id=atest.type.id)]
        searchstr = """
        SELECT test.id
        FROM test, test_arguments_dict
        WHERE test.id=test_arguments_dict.containerid
        """

        for arg in atest.arguments.all():
            tmpsearch = "AND test.id in (%s) " % string.join([str(x) for x in res], ', ')
            tmpsearch += "AND test_arguments_dict.name=%s "
            if arg.txtvalue:
                tmpsearch += "AND test_arguments_dict.txtvalue=%s "
                val = arg.txtvalue
            elif arg.intvalue:
                tmpsearch += "AND test_arguments_dict.intvalue=%s "
                val = arg.intvalue
            else:
                tmpsearch += "AND test_arguments_dict.blobvalue=%s "
                val = arg.blobvalue
            tmpres = self._fetchAll(searchstr+tmpsearch,
                                    [arg.name.id, val])
            res = []
            if tmpres == []:
                break
            tmp2 = list(zip(*tmpres)[0])
            for i in tmp2:
                if not i in res:
                    res.append(i)

        return [Test.objects.get(pk=i) for i in res]

    # FIXME : This is insanely crufty and not performant at all
    def compare(self, other):
        """
        Compares the tests from self and the tests from other.

        Returns a tuple of 5 values:
        * list of tests in other which are not in self
        * list of tests in self which are not in other
        * list of tests in self which have improved compared to the one in other
        * list of tests in self which have regressed compared to the one in other
        * a dictionnary mapping of:
          * test from self
          * corresponding test from other
        """
        if not isinstance(other, TestRun):
            raise TypeError
        newmapping = {}
        oldinnew = []
        newtests = []

        for othert in other.test_set.all():
            anc = self.find_test_similar_args(othert)
            if anc == []:
                newtests.append(othert)
            else:
                newmapping[othert] = anc
                oldinnew.extend(anc)
        testsgone = [x for x in self.test_set.all() if not x in oldinnew]

        return newmapping

    def __str__(self):
        return "Testrun #%d [%s]" % (self.id, self.starttime)

class TestManager(models.Manager):
    def failed(self):
        """Only returns the tests that succeeded"""
        return self.exclude(resultpercentage=100.0)

    def succeeded(self):
        """Only returns the tests that failed (either totally or partially)"""
        return self.filter(resultpercentage=100.0)

    def scenarios(self):
        """Filters the QuerySet to only contain scenarios (i.e. container tests)"""
        return self.extra(where=["subtests.scenarioid=test.id"], tables=["subtests"])

    def leaftests(self):
        """Filters the QuerySet to only contain leaf tests (i.e. not scenarios)"""
        return self.filter(subtest=None)

    def timedout(self):
        """Filters the QuerySet to only return tests that timed out"""
        # timed-out tests are definitely failed
        return self.failed().exclude(checklist__name__name="no-timeout",
                                     checklist__value=1)

class Test(models.Model):
    objects = TestManager()
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    testrunid = models.ForeignKey(TestRun, db_column="testrunid")
    type = models.ForeignKey(TestClassInfo, db_column="type",
                             related_name="instances")
    resultpercentage = models.TextField(blank=True) # This field type is a guess.

    def get_absolute_url(self):
        return ('web.insanity.views.test_summary', [str(self.id)])
    get_absolute_url = permalink(get_absolute_url)

    def is_scenario(self):
        return bool(SubTest.objects.filter(scenarioid=self.id).count())

    def _is_subtest(self):
        return bool(SubTest.objects.filter(testid=self.id).count())
    is_subtest = property(_is_subtest)

    def _is_success(self):
        return bool(self.resultpercentage == 100.0)
    is_success = property(_is_success)

    def _get_results_dict(self, checklist=None, allchecks=None):
        """
        Returns an ordered list of check results as dictionnaries.
        dictionnary:
          'type': TestClassInfoCheckListDict
          'value': TestCheckListList
          'skipped': boolean set to True if check was skipped

        This differs from checklist_set in the sense that it will indicate
        the skipped check items.
        """
        res = []

        # pre-computed fullchecklist
        if checklist == None:
            fcl = self.type.fullchecklist
        else:
            fcl = checklist

        # pre-computer checklist
        if allchecks:
            v = [x for x in allchecks if x.containerid == self]
        else:
            v = self.checklist.all().select_related("name","value") # v.name == fcl.id

        for checktype in fcl:
            d = {}
            d['type'] = checktype
            val = None
            for av in v:
                if checktype == av.name:
                    d['skipped'] = False
                    val = av.value
                    break
            if val == None:
                d['skipped'] = True
            d['value'] = val
            res.append(d)
        return res
    results = property(_get_results_dict)

    def _get_full_arguments(self, fullarguments=None, allargs=None):
        """
        Returns an ordered list of arguments

        This differs from test.arguments.all in the sense that it will also
        contains the arguments with defaults values
        """
        res = []

        # pre-computed fullarguments
        if fullarguments == None:
            fa = self.type.fullarguments
        else:
            fa = fullarguments

        # pre-computed arguments
        if allargs:
            v = [x for x in allargs if x.containerid == self]
        else:
            v = self.arguments.all().select_related(depth=1)

        for argtype in fa:
            d = {}
            d['type'] = argtype
            val = None
            for av in v:
                if argtype == av.name:
                    d['skipped'] = False
                    val = av.value
                    break
            if val == None:
                d['skipped'] = True
            d['value'] = val
            res.append(d)
        return res
    fullarguments = property(_get_full_arguments)

    def _test_error(self, allextras=None):
        """ Returns the error TestExtraInfoDict if available"""

        def stringify_gst_error(anerr):
            quarkmap = {
                "gst-core-error-quark" : "CORE_ERROR",
                "gst-library-error-quark" : "LIBRARY_ERROR",
                "gst-resource-error-quark" : "RESOURCE_ERROR",
                "gst-stream-error-quark" : "STREAM_ERROR"
                }
            quark,message = anerr[1:3]
            return "%s: %s" % (quarkmap.get(quark, "UNKNOWN_ERROR"),
                               message)

        def stringify_return_code(retcodestr):
            retmap = {
                -1:"SIGHUP",
                -2:"SIGINT",
                -3:"SIGQUIT",
                -4:"SIGILL",
                -6:"SIGABRT",
                -8:"SIGFPE",
                -9:"SIGKILL",
                -11:"SIGSEGV",
                }
            ret = None
            retcode = long(retcodestr)
            if retcode:
                if retcode in retmap:
                    ret = "Process return code : %s [%d]" % (retmap[retcode],retcode)
                else:
                    ret = "Process return code : %d" % retcode
            return ret

        err = None

        # pre-computed extras
        if allextras != None:
            errs = [x for x in allextras if x.containerid==self and x.name.name in ["subprocess-return-code","errors"]]
        else:
            try:
                errs = self.extrainfo.all().select_related("name__name", "intvalue","txtvalue","blobvalue").filter(name__name__in=["errors", "subprocess-return-code"])
            except:
                errs = []

        if len(errs) == 0:
            return None

        errs = errs[0]
        if errs.name.name == "errors":
            err = stringify_gst_error(errs.value[0])
        else: # it can only be subprocess-return-code
            err = stringify_return_code(errs.intvalue)

        return err
    test_error = property(_test_error)

    class Meta:
        db_table = 'test'

    def __str__(self):
        return "%s:%s" % (self.type.type, self.id)

class SubTest(models.Model):
    testid = models.OneToOneField(Test, db_column="testid",
                                  related_name="parent",
                                  primary_key=True)
    scenarioid = models.ForeignKey(Test, db_column="scenarioid",
                                   related_name="subtest")
    class Meta:
        db_table = 'subtests'

class Monitor(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    testid = models.ForeignKey(Test, db_column="testid")
    type = models.ForeignKey(MonitorClassInfo, db_column="type",
                             related_name="instances")
    resultpercentage = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'monitor'

class MonitorArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid",
                                    related_name="arguments")
    name = models.ForeignKey(MonitorClassInfoArgumentsDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        # our magic to figure out the type of the value
        if not self.intvalue == None:
            return self.intvalue
        if not self.txtvalue == None:
            return self.txtvalue
        return loads(str(self.blobvalue))
    value = property(_get_value)

    class Meta:
        db_table = 'monitor_arguments_dict'

    def __str__(self):
        return "%s:%s" % (self.name.name, self.value)


class MonitorChecklistDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid",
                                    related_name="checklist")
    name = models.ForeignKey(MonitorClassInfoCheckListDict,
                             db_column="name")
    containerid = models.IntegerField(null=True, blank=True)
    name = models.IntegerField(null=True, blank=True)
    value = models.IntegerField(null=True, blank=True,
                                db_column="intvalue")
    class Meta:
        db_table = 'monitor_checklist_dict'

class MonitorExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid",
                                    related_name="extrainfos")
    name = models.ForeignKey(MonitorClassInfoExtraInfoDict,
                             db_column="name")
    containerid = models.IntegerField(null=True, blank=True)
    name = models.IntegerField(null=True, blank=True)
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        # our magic to figure out the type of the value
        if not self.intvalue == None:
            return self.intvalue
        if not self.txtvalue == None:
            return self.txtvalue
        return loads(str(self.blobvalue))
    value = property(_get_value)

    class Meta:
        db_table = 'monitor_extrainfo_dict'

class MonitorOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid",
                                    related_name="outputfiles")
    name = models.ForeignKey(MonitorClassInfoOutputFilesDict,
                             db_column="name")
    value = models.TextField(blank=True, db_column="txtvalue")

    def _get_basename(self):
        return os.path.basename(self.value)
    basename = property(_get_basename)

    class Meta:
        db_table = 'monitor_outputfiles_dict'

class TestArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid",
                                    related_name="arguments")
    name = models.ForeignKey(TestClassInfoArgumentsDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        # our magic to figure out the type of the value
        if not self.intvalue == None:
            return self.intvalue
        if not self.txtvalue == None:
            return self.txtvalue
        try:
            val = loads(str(self.blobvalue))
        except:
            val = "Non-pickleable value, fix test"
        return val
    value = property(_get_value)

    class Meta:
        db_table = 'test_arguments_dict'

    def __str__(self):
        return "%s:%s" % (self.name.name, self.value)

class TestCheckListList(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid",
                                    related_name="checklist")
    name = models.ForeignKey(TestClassInfoCheckListDict,
                             db_column="name")
    value = models.IntegerField(null=True, blank=True,
                                db_column="intvalue")
    class Meta:
        db_table = 'test_checklist_list'

class TestOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid",
                                    related_name="outputfiles")
    name = models.ForeignKey(TestClassInfoOutputFilesDict,
                             db_column="name")
    value = models.TextField(blank=True, db_column="txtvalue")
    class Meta:
        db_table = 'test_outputfiles_dict'

class TestExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid",
                                    related_name="extrainfo")
    name = models.ForeignKey(TestClassInfoExtraInfoDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        # our magic to figure out the type of the value
        if not self.intvalue == None:
            return self.intvalue
        if not self.txtvalue == None:
            return self.txtvalue
        return loads(str(self.blobvalue))
    value = property(_get_value)

    class Meta:
        db_table = 'test_extrainfo_dict'

class TestRunEnvironmentDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestRun, db_column="containerid",
                                    related_name="environment")
    name = models.TextField(blank=True)
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.

    def _get_value(self):
        # our magic to figure out the type of the value
        if not self.intvalue == None:
            return self.intvalue
        if not self.txtvalue == None:
            return self.txtvalue
        return loads(str(self.blobvalue))
    value = property(_get_value)

    class Meta:
        db_table = 'testrun_environment_dict'

class Version(models.Model):
    version = models.IntegerField(null=True, blank=True)
    modificationtime = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'version'
