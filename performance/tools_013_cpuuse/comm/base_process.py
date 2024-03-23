#!/usr/bin/env python
import logging
from logging.handlers import RotatingFileHandler
import sys
import cutils
import os

class BaseProcess(object):
    def __init__(self, config_path, section_name):        
        self.__config = cutils.generate_config(config_path, section_name)
        self.__logger = None
        
        log_config = cutils.generate_config(config_path, 'log')
        if len(log_config) > 0:
            self.__logger = self.__init_log(log_config['path'] + '/' + section_name + '.log', log_config['level'], int(log_config['size']))
        else:
            #if no log configure , write it to the console
            print 'NOTICE!! no log configuration found, write log to stdout'
            self.__logger = cutils.console_logger()
       
        self.__logger.info("start %s , pid = %d" % (section_name, os.getpid()))

       
    def __init_log(self, name, level, size):
        LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL
        }
        if not LEVELS.has_key(level):
            level = 'error'
        logger = logging.getLogger()
        common_log_h = RotatingFileHandler(filename=name,mode='a',maxBytes=size*1024*1024,backupCount=10)
        formatter_common = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(lineno)d [%(process)d] [%(threadName)s] %(message)s')
        common_log_h.setFormatter(formatter_common)
        logger.addHandler(common_log_h)
        logger.setLevel(LEVELS[level])
        return logger
        
    def get_config(self, key):
        return self.__config.get(key)
    
    def logger(self):
        return self.__logger

    
