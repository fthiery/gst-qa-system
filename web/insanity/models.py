import time
import string
from cPickle import dumps, loads
from django.db import models
from django.db.models import permalink
from django.db import connection

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

class TestClassInfo(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    type = models.TextField(blank=True)
    parent = models.ForeignKey("self", to_field="type",
                               db_column="parent",
                               related_name="subclass")
    description = models.TextField(blank=True)
    fulldescription = models.TextField(blank=True)

    def _get_fullchecklist(self):
        print self.parent_id, self.checklist.all()
        if self.parent_id:
            res = list(self.parent.fullchecklist)
            res.extend(list(self.checklist.order_by("id")))
        else:
            res = list(self.checklist.order_by("id"))
        return res
    fullchecklist = property(_get_fullchecklist)

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
    value = models.TextField(blank=True, db_column="txtvalue")
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

class TestRun(models.Model, CustomSQLInterface):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    clientid = models.ForeignKey(Client, db_column="clientid")
    starttime = models.IntegerField(null=True, blank=True)
    stoptime = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'testrun'

    def get_absolute_url(self):
        return ('web.insanity.views.testrun_summary', [str(self.id)])
    get_absolute_url = permalink(get_absolute_url)

    def find_test_similar_args(self, atest):
        """Returns tests which have the similar arguments as atest"""
        # this query is too complex to do with DJango code
        # if somebody can convert it to django code, you're welcome
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

        before = time.time()
        for othert in other.test_set.all():
            anc = self.find_test_similar_args(othert)
            if anc == []:
                newtests.append(othert)
            else:
                newmapping[othert] = anc
                oldinnew.extend(anc)
        med = time.time()
        testsgone = [x for x in self.test_set.all() if not x in oldinnew]

        after = time.time()
        print "it took %.2fs/%.2fs to find similar tests" % (med - before,
                                                             after - before)
        return newmapping

    def __str__(self):
        return "Testrun #%d [%s]" % (self.id, time.ctime(self.starttime))

class Test(models.Model):
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

