'''
Created on Oct 30, 2014

@author: omarcillo
'''
import os.path as os_path
import sys
import configparser


class Base(object):
    '''
    Base class for Infrapy
    '''
    general = 'GeneralParams'

    def __init__(self, conf_file: str, task: str):
        '''
        init a Base infrapy class

        :param conf_file: configuration file path
        :param task: task name
        '''
        self.general_PARAM = {}
        self.task_PARAM = {}
        self.db_connected = False
        self.data_retrieved = False
        self.data_processed = False
        self.result_submitted = False
        if not conf_file:
            print('Error: configuration file is not defined')
            sys.exit(1)
        if not os_path.isfile(conf_file):
            print('Error: configuration file does not exist in directory')
            sys.exit(2)
        Config = configparser.ConfigParser()
        Config.read(conf_file)
        self.db_PARAM = dict(Config.items('database'))
        self.general_PARAM = dict(Config.items(self.general))
        self.task_PARAM = dict(Config.items(task))
        print('\n GENERAL PARAMETERS')
        for il in self.general_PARAM:
            print(il, self.general_PARAM[il])
        print('\n DB CONNECTION')
        for il in self.db_PARAM:
            print(il, self.db_PARAM[il])
        print('\n TASK PARAMETERS')
        for il in self.task_PARAM:
            print(il, self.task_PARAM[il])

    @classmethod
    def database_connecting(cls):
        '''
        Base class for connecting database
        Recommended to be overridden by your class
        '''
        return cls.db_connected

    @classmethod
    def data_retrieving(cls):
        '''
        Base class for retrieving data
        Recommended to be overridden by your class
        '''
        return cls.data_retrieved

    @classmethod
    def data_processing(cls):
        '''
        Base class for processing data
        Recommended to be overridden by your class
        '''
        return cls.data_processed

    @classmethod
    def results_submitting(cls):
        '''
        Base class for submitting results
        Recommended to be overridden by your class
        '''
        return cls.result_submitted

    @classmethod
    def database_disconnecting(cls):
        '''
        Base class for disconnecting database
        Recommended to be overridden by your class
        '''
        return cls.db_connected
