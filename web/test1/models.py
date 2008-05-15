# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.db import models

class Client(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    software = models.TextField(blank=True)
    name = models.TextField(blank=True)
    user = models.TextField(blank=True)
    class Meta:
        db_table = 'client'

class MonitorClassInfo(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    type = models.TextField(blank=True)
    parent = models.ForeignKey("self", db_column="parent")
    description = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo'

class MonitorClassInfoArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo_arguments_dict'

class MonitorClassInfoCheckListDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo_checklist_dict'

class MonitorClassInfoExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo_extrainfo_dict'

class MonitorClassInfoOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(MonitorClassInfo,
                                    db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'monitorclassinfo_outputfiles_dict'

class TestClassInfo(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    type = models.TextField(blank=True)
    parent = models.ForeignKey("self", to_field="type", db_column="parent")
    description = models.TextField(blank=True)
    fulldescription = models.TextField(blank=True)
    class Meta:
        db_table = 'testclassinfo'

class TestClassInfoArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.IntegerField(null=True, blank=True)
    name = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'testclassinfo_arguments_dict'

class TestClassInfoCheckListDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo, db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'testclassinfo_checklist_dict'

class TestClassInfoExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo, db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'testclassinfo_extrainfo_dict'

class TestClassInfoOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestClassInfo, db_column="containerid")
    name = models.TextField(blank=True)
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'testclassinfo_outputfiles_dict'

class TestRun(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    clientid = models.ForeignKey(Client, db_column="clientid")
    starttime = models.IntegerField(null=True, blank=True)
    stoptime = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'testrun'

class Test(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    testrunid = models.ForeignKey(TestRun, db_column="testrunid")
    type = models.ForeignKey(TestClassInfo, db_column="type")
    resultpercentage = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'test'

class Subtests(models.Model):
    testid = models.ForeignKey(Test, db_column="testid",
                               related_name="parent",
                               primary_key=True)
    scenarioid = models.ForeignKey(Test, db_column="scenarioid",
                                   related_name="subtest")
    class Meta:
        db_table = 'subtests'

class Monitor(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    testid = models.ForeignKey(Test, db_column="testid")
    type = models.ForeignKey(MonitorClassInfo, db_column="type")
    resultpercentage = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'monitor'

class MonitorArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid")
    name = models.ForeignKey(MonitorClassInfoArgumentsDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'monitor_arguments_dict'

class MonitorChecklistDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid")
    name = models.ForeignKey(MonitorClassInfoCheckListDict,
                             db_column="name")
    containerid = models.IntegerField(null=True, blank=True)
    name = models.IntegerField(null=True, blank=True)
    intvalue = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'monitor_checklist_dict'

class MonitorExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid")
    name = models.ForeignKey(MonitorClassInfoExtraInfoDict,
                             db_column="name")
    containerid = models.IntegerField(null=True, blank=True)
    name = models.IntegerField(null=True, blank=True)
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'monitor_extrainfo_dict'

class MonitorOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Monitor, db_column="containerid")
    name = models.ForeignKey(MonitorClassInfoOutputFilesDict,
                             db_column="name")
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'monitor_outputfiles_dict'

class TestArgumentsDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid")
    name = models.ForeignKey(TestClassInfoArgumentsDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'test_arguments_dict'

class TestCheckListList(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid")
    name = models.ForeignKey(TestClassInfoCheckListDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'test_checklist_list'

class TestOutputFilesDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid")
    name = models.ForeignKey(TestClassInfoOutputFilesDict,
                             db_column="name")
    txtvalue = models.TextField(blank=True)
    class Meta:
        db_table = 'test_outputfiles_dict'

class TestExtraInfoDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(Test, db_column="containerid")
    name = models.ForeignKey(TestClassInfoExtraInfoDict,
                             db_column="name")
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'test_extrainfo_dict'

class TestRunEnvironmentDict(models.Model):
    id = models.IntegerField(null=True, primary_key=True, blank=True)
    containerid = models.ForeignKey(TestRun, db_column="containerid")
    name = models.TextField(blank=True)
    intvalue = models.IntegerField(null=True, blank=True)
    txtvalue = models.TextField(blank=True)
    blobvalue = models.TextField(blank=True) # This field type is a guess.
    class Meta:
        db_table = 'testrun_environment_dict'

class Version(models.Model):
    version = models.IntegerField(null=True, blank=True)
    modificationtime = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = 'version'

